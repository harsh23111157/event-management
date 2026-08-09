"""Web views for events and workflow actions."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.finance.models import Expense, ExpenseCategory
from apps.operations.models import EventStaff, EventTask, TaskStatus

from .forms import EventForm
from .models import Event, EventStatus
from .services import EventWorkflowService


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        qs = Event.objects.select_related("venue", "manager")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        if self.request.user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=self.request.user).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = EventStatus.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        qs = Event.objects.select_related("venue", "manager")
        if self.request.user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=self.request.user).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        ctx["tasks"] = event.tasks.select_related("assigned_to").all()
        ctx["staff_list"] = event.staff_assignments.select_related("staff").all()
        ctx["vendors"] = event.vendor_assignments.select_related("vendor").all()
        ctx["expenses"] = event.expenses.select_related("created_by", "approved_by").all()
        ctx["can_manage"] = is_event_manager_or_admin(self.request.user)
        ctx["can_approve"] = self.request.user.is_admin
        ctx["can_finance"] = self.request.user.is_admin or self.request.user.is_finance
        approved = sum(e.amount for e in ctx["expenses"] if e.status == "APPROVED")
        ctx["approved_expenses_total"] = approved
        ctx["remaining_budget"] = float(event.budget) - float(approved)
        ctx["utilization"] = round(approved / float(event.budget) * 100, 1) if event.budget else 0
        return ctx


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.audit.services import AuditService
        from apps.events.validators import EventValidationService
        event = form.save(commit=False)
        conflict = EventValidationService.validate_venue_conflict(event)
        if conflict:
            form.add_error(None, conflict)
            return self.form_invalid(form)
        event.save()
        AuditService.log(self.request.user, "EVENT_CREATE", "event", event.id, f"Created event '{event.name}'")
        messages.success(self.request, f"Event '{event.name}' created.")
        return redirect("event_detail", pk=event.id)


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Event.objects.all()
        if not self.request.user.is_admin:
            qs = qs.filter(manager=self.request.user)
        return qs

    def form_valid(self, form):
        from apps.audit.services import AuditService
        event = form.save(commit=False)
        if event.status not in (EventStatus.DRAFT, EventStatus.REJECTED, EventStatus.SUBMITTED):
            messages.error(self.request, "Completed or in-progress events cannot be edited.")
            return redirect("event_detail", pk=event.id)
        conflict = None
        if event.status in (EventStatus.DRAFT, EventStatus.REJECTED):
            from apps.events.validators import EventValidationService
            conflict = EventValidationService.validate_venue_conflict(event)
        if conflict:
            form.add_error(None, conflict)
            return self.form_invalid(form)
        event.save()
        AuditService.log(self.request.user, "EVENT_UPDATE", "event", event.id, f"Updated event '{event.name}'")
        messages.success(self.request, f"Event '{event.name}' updated.")
        return redirect("event_detail", pk=event.id)


class EventWorkflowActionView(LoginRequiredMixin, View):
    """Handles submit / approve / reject / start / complete / cancel / return-to-draft."""

    def post(self, request, pk, action):
        event = get_object_or_404(Event, pk=pk)
        try:
            if action == "submit":
                EventWorkflowService.submit_event(event, request.user)
                messages.success(request, "Event submitted for approval.")
            elif action == "approve":
                EventWorkflowService.approve_event(event, request.user)
                messages.success(request, "Event approved.")
            elif action == "reject":
                reason = request.POST.get("reason", "").strip()
                EventWorkflowService.reject_event(event, request.user, reason)
                messages.success(request, "Event rejected.")
            elif action == "start":
                EventWorkflowService.start_event(event, request.user)
                messages.success(request, "Event started.")
            elif action == "complete":
                EventWorkflowService.complete_event(event, request.user)
                messages.success(request, "Event completed.")
            elif action == "cancel":
                EventWorkflowService.cancel_event(event, request.user)
                messages.success(request, "Event cancelled.")
            elif action == "return_draft":
                EventWorkflowService.return_to_draft(event, request.user)
                messages.success(request, "Event returned to draft.")
            else:
                messages.error(request, "Unknown action.")
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect("event_detail", pk=event.id)
