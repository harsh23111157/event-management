"""Web views for events and workflow actions."""
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.audit.models import AuditLog
from apps.finance.models import Expense, ExpenseCategory, ExpenseStatus
from apps.operations.models import Attendance, EventStaff, EventTask, Schedule, TaskPriority, TaskStatus

from .forms import EventForm
from .models import Event, EventStatus, EventType
from .services import EventReadinessService, EventWorkflowService


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user
        qs = Event.objects.select_related("venue", "manager").prefetch_related("tasks", "staff_assignments")

        # Role scoping
        if user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=user).distinct()
        elif user.is_event_manager:
            qs = qs.filter(manager=user)
        # Admin and Finance see all events

        # Search filter
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(venue__name__icontains=search) |
                Q(manager__first_name__icontains=search) |
                Q(manager__last_name__icontains=search) |
                Q(manager__username__icontains=search)
            )

        # Status filter
        status_filter = self.request.GET.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Event type filter
        type_filter = self.request.GET.get("type", "").strip()
        if type_filter:
            qs = qs.filter(event_type=type_filter)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Base counts for pipeline chips
        base_qs = Event.objects.all()
        if user.is_staff_member:
            base_qs = base_qs.filter(staff_assignments__staff=user).distinct()
        elif user.is_event_manager:
            base_qs = base_qs.filter(manager=user)

        ctx["status_counts"] = {
            "all": base_qs.count(),
            "DRAFT": base_qs.filter(status=EventStatus.DRAFT).count(),
            "SUBMITTED": base_qs.filter(status=EventStatus.SUBMITTED).count(),
            "APPROVED": base_qs.filter(status=EventStatus.APPROVED).count(),
            "IN_PROGRESS": base_qs.filter(status=EventStatus.IN_PROGRESS).count(),
            "COMPLETED": base_qs.filter(status=EventStatus.COMPLETED).count(),
            "CANCELLED": base_qs.filter(status=EventStatus.CANCELLED).count(),
            "REJECTED": base_qs.filter(status=EventStatus.REJECTED).count(),
        }
        ctx["status_choices"] = EventStatus.choices
        ctx["type_choices"] = EventType.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["can_create_event"] = is_event_manager_or_admin(user)
        return ctx


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        user = self.request.user
        qs = Event.objects.select_related("venue", "manager")
        if user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=user).distinct()
        elif user.is_event_manager:
            # Event manager can only view their own events
            qs = qs.filter(manager=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        user = self.request.user

        # Detailed related entities
        tasks_qs = event.tasks.select_related("assigned_to").all()
        ctx["tasks"] = tasks_qs
        ctx["staff_list"] = event.staff_assignments.select_related("staff").all()
        ctx["vendors"] = event.vendor_assignments.select_related("vendor").all()
        ctx["schedules"] = event.schedules.select_related("responsible_staff__staff").all()
        ctx["attendances"] = event.attendances.select_related("staff").all()
        ctx["activity_logs"] = AuditLog.objects.filter(entity_type="event", entity_id=event.id).select_related("user").order_by("-timestamp")[:15]

        # Financial breakdown (safely calculate Decimals)
        expenses_qs = event.expenses.select_related("created_by", "approved_by").all()
        ctx["expenses"] = expenses_qs
        approved_expenses = sum(e.amount for e in expenses_qs if e.status == ExpenseStatus.APPROVED)
        pending_expenses = sum(e.amount for e in expenses_qs if e.status == ExpenseStatus.PENDING)
        ctx["approved_expenses_total"] = approved_expenses
        ctx["pending_expenses_total"] = pending_expenses

        budget_float = float(event.budget) if event.budget else 0.0
        approved_float = float(approved_expenses)
        ctx["remaining_budget"] = budget_float - approved_float
        ctx["utilization"] = round((approved_float / budget_float * 100), 1) if budget_float > 0 else 0.0

        # Operational Readiness
        ctx["readiness"] = EventReadinessService.calculate_readiness(event)

        # Task Progress Stats
        total_tasks = tasks_qs.count()
        completed_tasks = tasks_qs.filter(status=TaskStatus.COMPLETED).count()
        in_prog_tasks = tasks_qs.filter(status=TaskStatus.IN_PROGRESS).count()
        blocked_tasks = tasks_qs.filter(status=TaskStatus.BLOCKED).count()
        todo_tasks = tasks_qs.filter(status=TaskStatus.TODO).count()
        critical_open = tasks_qs.filter(priority=TaskPriority.CRITICAL).exclude(status=TaskStatus.COMPLETED).count()

        ctx["task_stats"] = {
            "total": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_prog_tasks,
            "blocked": blocked_tasks,
            "todo": todo_tasks,
            "critical_open": critical_open,
            "completion_pct": round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0,
        }

        # Role and Action Permissions
        ctx["is_event_owner"] = (event.manager_id == user.id)
        ctx["can_manage"] = user.is_admin or (user.is_event_manager and event.manager_id == user.id)
        can_edit = (user.is_admin or (user.is_event_manager and event.manager_id == user.id)) and event.status in (EventStatus.DRAFT, EventStatus.REJECTED)
        ctx["can_edit"] = can_edit
        ctx["can_edit_event"] = can_edit
        ctx["can_approve"] = user.is_admin
        ctx["can_finance"] = user.is_admin or user.is_finance
        ctx["active_tab"] = self.request.GET.get("tab", "overview")

        return ctx


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only Event Managers and Administrators can create events.")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_event_manager:
            initial["manager"] = self.request.user
        return initial

    def form_valid(self, form):
        from apps.audit.services import AuditService
        from apps.events.validators import EventValidationService
        event = form.save(commit=False)
        if self.request.user.is_event_manager:
            event.manager = self.request.user
        conflict = EventValidationService.validate_venue_conflict(event)
        if conflict:
            form.add_error(None, conflict)
            return self.form_invalid(form)
        event.save()
        AuditService.log(self.request.user, "EVENT_CREATE", "event", event.id, f"Created event '{event.name}'")
        messages.success(self.request, f"Event '{event.name}' created successfully.")
        return redirect("event_detail", pk=event.id)


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Event, pk=self.kwargs["pk"])

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        if not (user.is_admin or (user.is_event_manager and self.object.manager_id == user.id)):
            raise PermissionDenied("You do not have permission to edit this event.")
        if self.object.status not in (EventStatus.DRAFT, EventStatus.REJECTED):
            raise PermissionDenied(f"Event is in '{self.object.get_status_display()}' status and locked from direct edits.")
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
        AuditService.log(self.request.user, "EVENT_UPDATE", "event", event.id, f"Updated event '{event.name}'")
        messages.success(self.request, f"Event '{event.name}' updated successfully.")
        return redirect("event_detail", pk=event.id)


class EventWorkflowActionView(LoginRequiredMixin, View):
    """Handles submit / approve / reject / start / complete / cancel / return-to-draft."""

    def post(self, request, pk, action):
        event = get_object_or_404(Event, pk=pk)
        from apps.operations.models import NotificationService, NotificationType
        try:
            if action == "submit":
                EventWorkflowService.submit_event(event, request.user)
                messages.success(request, f"Event '{event.name}' submitted for approval.")
            elif action == "approve":
                EventWorkflowService.approve_event(event, request.user)
                if event.manager:
                    NotificationService.send(
                        recipient=event.manager,
                        title=f"Event Approved: {event.name}",
                        message=f"Your event '{event.name}' has been approved by Administrator {request.user.get_full_name() or request.user.username}.",
                        notification_type=NotificationType.EVENT_STATUS,
                        link=f"/events/{event.id}/",
                    )
                messages.success(request, f"Event '{event.name}' approved successfully.")
            elif action == "reject":
                reason = request.POST.get("reason", "").strip()
                EventWorkflowService.reject_event(event, request.user, reason)
                if event.manager:
                    NotificationService.send(
                        recipient=event.manager,
                        title=f"Event Returned: {event.name}",
                        message=f"Your event '{event.name}' was returned for revision. Reason: {reason or 'Not specified'}",
                        notification_type=NotificationType.EVENT_STATUS,
                        link=f"/events/{event.id}/",
                    )
                messages.warning(request, f"Event '{event.name}' has been rejected.")
            elif action == "start":
                EventWorkflowService.start_event(event, request.user)
                messages.success(request, f"Event '{event.name}' is now in progress.")
            elif action == "complete":
                EventWorkflowService.complete_event(event, request.user)
                messages.success(request, f"Event '{event.name}' marked as completed.")
            elif action == "cancel":
                EventWorkflowService.cancel_event(event, request.user)
                messages.warning(request, f"Event '{event.name}' has been cancelled.")
            elif action == "return_draft":
                EventWorkflowService.return_to_draft(event, request.user)
                messages.info(request, f"Event '{event.name}' returned to draft status.")
            else:
                messages.error(request, "Unknown workflow action.")
        except PermissionError as exc:
            raise PermissionDenied(str(exc))
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("event_detail", pk=event.id)


