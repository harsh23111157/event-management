"""Web views for tasks, staff, schedules, and attendance."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.events.models import Event

from .forms import EventStaffForm, EventTaskForm, ScheduleForm, StaffTaskUpdateForm
from .models import Attendance, AttendanceStatus, EventStaff, EventTask, Schedule, TaskPriority, TaskStatus


class TaskListView(LoginRequiredMixin, ListView):
    model = EventTask
    template_name = "operations/task_list.html"
    context_object_name = "tasks"
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        qs = EventTask.objects.select_related("event", "assigned_to", "event__venue")

        # Role scoping
        if user.is_staff_member:
            qs = qs.filter(assigned_to=user)
        elif user.is_event_manager:
            qs = qs.filter(event__manager=user)
        # Admin and Finance see all tasks

        # Filters
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(event__name__icontains=search) |
                Q(assigned_to__first_name__icontains=search) |
                Q(assigned_to__last_name__icontains=search)
            )

        status_val = self.request.GET.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)

        priority_val = self.request.GET.get("priority", "").strip()
        if priority_val:
            qs = qs.filter(priority=priority_val)

        event_id = self.request.GET.get("event", "").strip()
        if event_id and event_id.isdigit():
            qs = qs.filter(event_id=int(event_id))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        base_qs = EventTask.objects.all()
        if user.is_staff_member:
            base_qs = base_qs.filter(assigned_to=user)
        elif user.is_event_manager:
            base_qs = base_qs.filter(event__manager=user)

        now = timezone.now()
        ctx["status_counts"] = {
            "all": base_qs.count(),
            "TODO": base_qs.filter(status=TaskStatus.TODO).count(),
            "IN_PROGRESS": base_qs.filter(status=TaskStatus.IN_PROGRESS).count(),
            "COMPLETED": base_qs.filter(status=TaskStatus.COMPLETED).count(),
            "BLOCKED": base_qs.filter(status=TaskStatus.BLOCKED).count(),
            "overdue": base_qs.exclude(status=TaskStatus.COMPLETED).filter(due_date__lt=now).count(),
        }
        ctx["status_choices"] = TaskStatus.choices
        ctx["priority_choices"] = TaskPriority.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_priority"] = self.request.GET.get("priority", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["can_create_task"] = is_event_manager_or_admin(user)
        return ctx


class EventTaskCreateView(LoginRequiredMixin, CreateView):
    model = EventTask
    form_class = EventTaskForm
    template_name = "operations/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        user = request.user
        if not (user.is_admin or (user.is_event_manager and self.event.manager_id == user.id)):
            raise PermissionDenied("You can only create tasks for events you manage.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.event
        ctx["is_staff_edit"] = False
        return ctx

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.event
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        task = form.save()
        AuditService.log(self.request.user, "TASK_ASSIGN", "task", task.id,
                         f"Assigned task '{task.title}' to {task.assigned_to or 'Unassigned'} for {self.event.name}")
        messages.success(self.request, f"Task '{task.title}' created successfully.")
        return redirect("event_detail", pk=self.event.id)


class EventTaskUpdateView(LoginRequiredMixin, UpdateView):
    model = EventTask
    template_name = "operations/task_form.html"

    def get_form_class(self):
        if self.request.user.is_staff_member:
            return StaffTaskUpdateForm
        return EventTaskForm

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        if not self.request.user.is_staff_member:
            kw["event"] = self.object.event
        return kw

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(EventTask, pk=kwargs["pk"])
        user = request.user

        # Object-level permission checks
        if user.is_staff_member:
            if self.object.assigned_to_id != user.id:
                raise PermissionDenied("Staff members can only update tasks assigned to themselves.")
        elif user.is_event_manager:
            if self.object.event.manager_id != user.id:
                raise PermissionDenied("You can only update tasks for events you manage.")
        elif user.is_admin:
            pass  # Admin has full access
        else:
            raise PermissionDenied("You do not have permission to edit this task.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.object.event
        ctx["task"] = self.object
        ctx["is_staff_edit"] = self.request.user.is_staff_member
        return ctx

    def form_valid(self, form):
        from apps.audit.services import AuditService
        old_status = self.object.status
        task = form.save(commit=False)
        if task.status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            task.completed_at = timezone.now()
        elif task.status != TaskStatus.COMPLETED:
            task.completed_at = None
        task.save()
        if old_status != task.status:
            AuditService.log(self.request.user, "TASK_STATUS_CHANGE", "task", task.id,
                             f"Task '{task.title}' status changed: {old_status} -> {task.status}")
        messages.success(self.request, f"Task '{task.title}' updated successfully.")
        return redirect("task_list")


class EventStaffCreateView(LoginRequiredMixin, CreateView):
    model = EventStaff
    form_class = EventStaffForm
    template_name = "operations/staff_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        user = request.user
        if not (user.is_admin or (user.is_event_manager and self.event.manager_id == user.id)):
            raise PermissionDenied("You can only assign staff to events you manage.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.event
        return ctx

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.event
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        assignment = form.save()
        AuditService.log(self.request.user, "STAFF_ASSIGN", "eventstaff", assignment.id,
                         f"Assigned staff {assignment.staff.get_full_name()} to {self.event.name}")
        messages.success(self.request, f"Staff '{assignment.staff.get_full_name()}' assigned to event.")
        return redirect("event_detail", pk=self.event.id)


class ScheduleCreateView(LoginRequiredMixin, CreateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "operations/schedule_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        user = request.user
        if not (user.is_admin or (user.is_event_manager and self.event.manager_id == user.id)):
            raise PermissionDenied("You can only create schedules for events you manage.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.event
        return ctx

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.event
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        schedule = form.save(commit=False)
        schedule.event = self.event
        try:
            schedule.full_clean()
        except Exception as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        schedule.save()
        AuditService.log(self.request.user, "SCHEDULE_CREATE", "schedule", schedule.id,
                         f"Created schedule item '{schedule.title}' for {self.event.name}")
        messages.success(self.request, f"Schedule item '{schedule.title}' created.")
        return redirect("event_detail", pk=self.event.id)


class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = "operations/attendance_list.html"
    context_object_name = "attendances"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Attendance.objects.select_related("event", "staff")
        if user.is_staff_member:
            qs = qs.filter(staff=user)
        elif user.is_event_manager:
            qs = qs.filter(event__manager=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_staff_member:
            # Active assignments where staff can check in/out
            ctx["my_assignments"] = EventStaff.objects.filter(staff=user).select_related("event")
        return ctx


class AttendanceCheckInView(LoginRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        if not (user.is_admin or event.staff_assignments.filter(staff=user).exists()):
            raise PermissionDenied("You are not assigned to this event.")

        att, _ = Attendance.objects.get_or_create(event=event, staff=user)
        if not att.check_in:
            att.check_in = timezone.now()
            att.status = AttendanceStatus.PRESENT
            att.save()
            from apps.audit.services import AuditService
            AuditService.log(user, "ATTENDANCE_CHECKIN", "attendance", att.id, f"Checked in to {event.name}")
            messages.success(request, f"Checked in to {event.name} successfully.")
        else:
            messages.info(request, f"Already checked in at {att.check_in.strftime('%H:%M')}.")
        return redirect(request.META.get("HTTP_REFERER", "dashboard"))


class AttendanceCheckOutView(LoginRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        att = get_object_or_404(Attendance, event=event, staff=user)
        att.check_out = timezone.now()
        att.save()
        from apps.audit.services import AuditService
        AuditService.log(user, "ATTENDANCE_CHECKOUT", "attendance", att.id, f"Checked out of {event.name}")
        messages.success(request, f"Checked out of {event.name} successfully.")
        return redirect(request.META.get("HTTP_REFERER", "dashboard"))

