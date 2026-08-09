"""Web views for tasks, staff, and schedules."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.events.models import Event

from .forms import EventStaffForm, EventTaskForm, ScheduleForm
from .models import EventStaff, EventTask, Schedule, TaskStatus


class TaskListView(LoginRequiredMixin, ListView):
    model = EventTask
    template_name = "operations/task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        qs = EventTask.objects.select_related("event", "assigned_to")
        if self.request.user.is_staff_member:
            qs = qs.filter(assigned_to=self.request.user)
        return qs


class EventTaskCreateView(LoginRequiredMixin, CreateView):
    model = EventTask
    form_class = EventTaskForm
    template_name = "operations/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.event
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        task = form.save()
        AuditService.log(self.request.user, "TASK_ASSIGN", "task", task.id,
                         f"Assigned task '{task.title}' to {task.assigned_to}")
        messages.success(self.request, "Task created.")
        return redirect("event_detail", pk=self.event.id)


class EventTaskUpdateView(LoginRequiredMixin, UpdateView):
    model = EventTask
    form_class = EventTaskForm
    template_name = "operations/task_form.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.object.event
        return kw

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(EventTask, pk=kwargs["pk"])
        user = request.user
        if user.is_staff_member and self.object.assigned_to_id != user.id:
            return redirect("task_list")
        if not (user.is_staff_member or is_event_manager_or_admin(user)):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

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
                             f"Task '{task.title}' status {old_status} -> {task.status}")
        messages.success(self.request, "Task updated.")
        return redirect("task_list")


class EventStaffCreateView(LoginRequiredMixin, CreateView):
    model = EventStaff
    form_class = EventStaffForm
    template_name = "operations/staff_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.event
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        assignment = form.save()
        AuditService.log(self.request.user, "STAFF_ASSIGN", "eventstaff", assignment.id,
                         f"Assigned {assignment.staff} to {self.event.name}")
        messages.success(self.request, "Staff member assigned.")
        return redirect("event_detail", pk=self.event.id)


class ScheduleCreateView(LoginRequiredMixin, CreateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "operations/schedule_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

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
                         f"Schedule '{schedule.title}' for {self.event.name}")
        messages.success(self.request, "Schedule item created.")
        return redirect("event_detail", pk=self.event.id)
