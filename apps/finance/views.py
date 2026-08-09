"""Web views for expenses and financial operations."""
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from apps.accounts.permissions import is_event_manager_or_admin, is_finance_or_admin
from apps.events.models import Event
from apps.finance.forms import ExpenseForm, ExpenseRejectForm
from apps.finance.models import Expense, ExpenseCategory, ExpenseService, ExpenseStatus


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "finance/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        qs = Expense.objects.select_related("event", "created_by", "approved_by", "event__venue")

        # Role Scoping
        if user.is_staff_member:
            qs = qs.filter(event__staff_assignments__staff=user).distinct()
        elif user.is_event_manager:
            qs = qs.filter(event__manager=user)
        # Finance and Admin see all expenses

        # Filters
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(description__icontains=search) |
                Q(event__name__icontains=search) |
                Q(created_by__first_name__icontains=search) |
                Q(created_by__last_name__icontains=search)
            )

        status_val = self.request.GET.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)

        category_val = self.request.GET.get("category", "").strip()
        if category_val:
            qs = qs.filter(category=category_val)

        event_id = self.request.GET.get("event", "").strip()
        if event_id and event_id.isdigit():
            qs = qs.filter(event_id=int(event_id))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        base_qs = Expense.objects.all()
        if user.is_staff_member:
            base_qs = base_qs.filter(event__staff_assignments__staff=user).distinct()
        elif user.is_event_manager:
            base_qs = base_qs.filter(event__manager=user)

        approved_total = base_qs.filter(status=ExpenseStatus.APPROVED).aggregate(s=Sum("amount"))["s"] or Decimal(0)
        pending_total = base_qs.filter(status=ExpenseStatus.PENDING).aggregate(s=Sum("amount"))["s"] or Decimal(0)
        rejected_total = base_qs.filter(status=ExpenseStatus.REJECTED).aggregate(s=Sum("amount"))["s"] or Decimal(0)

        events_qs = Event.objects.exclude(status="CANCELLED")
        if user.is_event_manager:
            events_qs = events_qs.filter(manager=user)
        total_budget = events_qs.aggregate(s=Sum("budget"))["s"] or Decimal(0)

        ctx["approved_total"] = approved_total
        ctx["pending_total"] = pending_total
        ctx["rejected_total"] = rejected_total
        ctx["total_budget"] = total_budget
        ctx["remaining_budget"] = total_budget - approved_total
        ctx["utilization"] = round(float(approved_total) / float(total_budget) * 100, 1) if total_budget > 0 else 0.0

        ctx["status_counts"] = {
            "all": base_qs.count(),
            "PENDING": base_qs.filter(status=ExpenseStatus.PENDING).count(),
            "APPROVED": base_qs.filter(status=ExpenseStatus.APPROVED).count(),
            "REJECTED": base_qs.filter(status=ExpenseStatus.REJECTED).count(),
        }

        ctx["status_choices"] = ExpenseStatus.choices
        ctx["category_choices"] = ExpenseCategory.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_category"] = self.request.GET.get("category", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["can_approve"] = is_finance_or_admin(user)
        ctx["can_create_expense"] = is_finance_or_admin(user) or is_event_manager_or_admin(user)
        return ctx


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "finance/expense_form.html"
    success_url = reverse_lazy("expense_list")

    def dispatch(self, request, *args, **kwargs):
        if not (is_finance_or_admin(request.user) or is_event_manager_or_admin(request.user)):
            raise PermissionDenied("You do not have permission to submit expenses.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        expense = form.save(commit=False)
        expense.created_by = self.request.user

        # If user is Event Manager, verify they manage this event
        if self.request.user.is_event_manager and expense.event.manager_id != self.request.user.id:
            raise PermissionDenied("You can only log expenses for events you manage.")

        expense.save()
        AuditService.log(self.request.user, "EXPENSE_CREATE", "expense", expense.id,
                         f"Logged expense '{expense.description}' (₹{expense.amount}) for {expense.event.name}")
        messages.success(self.request, f"Expense '{expense.description}' created successfully.")
        return redirect("expense_list")


class ExpenseApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not is_finance_or_admin(request.user):
            raise PermissionDenied("Only Finance Officers and Administrators can approve expenses.")
        expense = get_object_or_404(Expense, pk=pk)
        try:
            ExpenseService.approve(expense, request.user)
            messages.success(request, f"Expense '{expense.description}' approved.")
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(request.META.get("HTTP_REFERER", "expense_list"))


class ExpenseRejectView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not is_finance_or_admin(request.user):
            raise PermissionDenied("Only Finance Officers and Administrators can reject expenses.")
        expense = get_object_or_404(Expense, pk=pk)
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "A reason is required to reject an expense.")
            return redirect(request.META.get("HTTP_REFERER", "expense_list"))
        try:
            ExpenseService.reject(expense, request.user, reason)
            messages.warning(request, f"Expense '{expense.description}' rejected.")
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(request.META.get("HTTP_REFERER", "expense_list"))

