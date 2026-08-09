"""Web views for expenses."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from apps.accounts.permissions import is_finance_or_admin, is_event_manager_or_admin
from apps.finance.forms import ExpenseForm, ExpenseRejectForm
from apps.finance.models import Expense, ExpenseStatus
from apps.finance.models import ExpenseService


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "finance/expense_list.html"
    context_object_name = "expenses"

    def get_queryset(self):
        qs = Expense.objects.select_related("event", "created_by", "approved_by")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = ExpenseStatus.choices
        ctx["can_approve"] = is_finance_or_admin(self.request.user)
        return ctx


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "finance/expense_form.html"
    success_url = reverse_lazy("expense_list")

    def dispatch(self, request, *args, **kwargs):
        if not (is_finance_or_admin(request) or is_event_manager_or_admin(request)):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.audit.services import AuditService
        expense = form.save(commit=False)
        expense.created_by = self.request.user
        expense.save()
        AuditService.log(self.request.user, "EXPENSE_CREATE", "expense", expense.id,
                         f"Created expense '{expense.description}' for {expense.event.name}")
        messages.success(self.request, "Expense created.")
        return redirect("expense_list")


class ExpenseApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        try:
            ExpenseService.approve(expense, request.user)
            messages.success(request, "Expense approved.")
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect("expense_list")


class ExpenseRejectView(LoginRequiredMixin, View):
    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        form = ExpenseRejectForm(request.POST)
        if form.is_valid():
            try:
                ExpenseService.reject(expense, request.user, form.cleaned_data["reason"])
                messages.success(request, "Expense rejected.")
            except (PermissionError, ValueError) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "A reason is required to reject an expense.")
        return redirect("expense_list")
