"""Web views for tasks, staff, schedules, attendance, and notifications."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.events.models import Event

from .forms import (
    EventStaffForm, EventTaskForm, ManagerAttendanceForm,
    ScheduleForm, StaffTaskUpdateForm
)
from .models import (
    Attendance, AttendanceStatus, EventStaff, EventTask,
    Notification, NotificationService, NotificationType,
    Schedule, TaskPriority, TaskStatus
)

User = get_user_model()


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


class GlobalEventTaskCreateView(LoginRequiredMixin, CreateView):
    """Allows creating a task from the global task list, selecting the event."""
    model = EventTask
    form_class = EventTaskForm
    template_name = "operations/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only Event Managers and Administrators can create tasks.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_global_create"] = True
        ctx["is_staff_edit"] = False
        return ctx

    def form_valid(self, form):
        from apps.audit.services import AuditService
        task = form.save()
        AuditService.log(self.request.user, "TASK_ASSIGN", "task", task.id,
                         f"Created task '{task.title}' for event '{task.event.name}' assigned to {task.assigned_to or 'Unassigned'}")
        messages.success(self.request, f"Task '{task.title}' created successfully.")
        return redirect("task_list")


class EventTaskCreateView(LoginRequiredMixin, CreateView):
    """Creates a task pre-scoped to a specific event."""
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
        kw["user"] = self.request.user
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
        kw["user"] = self.request.user
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
        from apps.operations.models import NotificationService, NotificationType
        old_status = self.object.status
        task = form.save(commit=False)
        if task.status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            task.completed_at = timezone.now()
        elif task.status != TaskStatus.COMPLETED:
            task.completed_at = None
        task.save()

        # Send notification to event manager if updated by staff
        if self.request.user.is_staff_member and task.event and task.event.manager:
            updater_name = self.request.user.get_full_name() or self.request.user.username
            NotificationService.send(
                recipient=task.event.manager,
                title=f"Task Progress Updated: {task.title}",
                message=f"{updater_name} updated task '{task.title}' to status '{task.get_status_display()}'. Notes: {task.notes or 'None'}",
                notification_type=NotificationType.TASK_UPDATED,
                link=f"/events/{task.event.id}/#tasks",
            )

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
        messages.success(self.request, f"Staff '{assignment.staff.get_full_name() or assignment.staff.username}' assigned to event.")
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
        if user.is_admin or user.is_event_manager:
            events_qs = Event.objects.filter(status__in=["APPROVED", "IN_PROGRESS"])
            if user.is_event_manager:
                events_qs = events_qs.filter(manager=user)
            ctx["active_events"] = events_qs
            ctx["can_manage_attendance"] = True
            ctx["status_choices"] = AttendanceStatus.choices
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
        return redirect(request.META.get("HTTP_REFERER", "attendance_list"))


class AttendanceCheckOutView(LoginRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        if not (user.is_admin or event.staff_assignments.filter(staff=user).exists()):
            raise PermissionDenied("You are not assigned to this event.")

        att, created = Attendance.objects.get_or_create(
            event=event,
            staff=user,
            defaults={"check_in": timezone.now(), "status": AttendanceStatus.PRESENT}
        )
        att.check_out = timezone.now()
        att.save()
        from apps.audit.services import AuditService
        AuditService.log(user, "ATTENDANCE_CHECKOUT", "attendance", att.id, f"Checked out of {event.name}")
        messages.success(request, f"Checked out of {event.name} successfully.")
        return redirect(request.META.get("HTTP_REFERER", "attendance_list"))



class ManagerAttendanceRecordView(LoginRequiredMixin, View):
    """Allows Event Managers and Admins to record or update attendance for any staff member in an event."""
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        if not (user.is_admin or (user.is_event_manager and event.manager_id == user.id)):
            raise PermissionDenied("You do not have permission to manage attendance for this event.")

        staff_id = request.POST.get("staff")
        status_val = request.POST.get("status", AttendanceStatus.PRESENT)
        check_in_str = request.POST.get("check_in")
        check_out_str = request.POST.get("check_out")

        if not staff_id:
            messages.error(request, "Please select a staff member.")
            return redirect(request.META.get("HTTP_REFERER", f"/events/{event.id}/#attendance"))

        staff_user = get_object_or_404(User, pk=staff_id)
        att, _ = Attendance.objects.get_or_create(event=event, staff=staff_user)
        att.status = status_val

        now = timezone.now()
        if check_in_str:
            try:
                from django.utils.dateparse import parse_datetime
                parsed_in = parse_datetime(check_in_str)
                if parsed_in:
                    att.check_in = timezone.make_aware(parsed_in) if timezone.is_naive(parsed_in) else parsed_in
            except Exception:
                pass
        elif not att.check_in and status_val == AttendanceStatus.PRESENT:
            att.check_in = now

        if check_out_str:
            try:
                from django.utils.dateparse import parse_datetime
                parsed_out = parse_datetime(check_out_str)
                if parsed_out:
                    att.check_out = timezone.make_aware(parsed_out) if timezone.is_naive(parsed_out) else parsed_out
            except Exception:
                pass

        att.save()
        from apps.audit.services import AuditService
        AuditService.log(user, "ATTENDANCE_UPDATE", "attendance", att.id,
                         f"Updated attendance for {staff_user.get_full_name() or staff_user.username} at {event.name} -> {att.get_status_display()}")
        messages.success(request, f"Attendance record updated for {staff_user.get_full_name() or staff_user.username}.")
        return redirect(request.META.get("HTTP_REFERER", f"/events/{event.id}/#attendance"))


class ManagerAttendanceQuickActionView(LoginRequiredMixin, View):
    """Quick check-in, check-out, or status change for a specific staff member by a manager."""
    def post(self, request, pk, action):
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        if not (user.is_admin or (user.is_event_manager and event.manager_id == user.id)):
            raise PermissionDenied("You do not have permission to manage attendance for this event.")

        staff_id = request.POST.get("staff_id")
        if not staff_id:
            messages.error(request, "Staff member ID required.")
            return redirect(request.META.get("HTTP_REFERER", f"/events/{event.id}/#attendance"))

        staff_user = get_object_or_404(User, pk=staff_id)
        att, _ = Attendance.objects.get_or_create(event=event, staff=staff_user)
        now = timezone.now()

        if action == "checkin":
            att.check_in = now
            att.status = AttendanceStatus.PRESENT
            messages.success(request, f"Marked {staff_user.get_full_name() or staff_user.username} as Checked In.")
        elif action == "checkout":
            att.check_out = now
            messages.success(request, f"Marked {staff_user.get_full_name() or staff_user.username} as Checked Out.")
        elif action == "late":
            att.status = AttendanceStatus.LATE
            if not att.check_in:
                att.check_in = now
            messages.info(request, f"Marked {staff_user.get_full_name() or staff_user.username} as Late.")
        elif action == "absent":
            att.status = AttendanceStatus.ABSENT
            att.check_in = None
            att.check_out = None
            messages.warning(request, f"Marked {staff_user.get_full_name() or staff_user.username} as Absent.")
        elif action == "present":
            att.status = AttendanceStatus.PRESENT
            if not att.check_in:
                att.check_in = now
            messages.success(request, f"Marked {staff_user.get_full_name() or staff_user.username} as Present.")

        att.save()
        return redirect(request.META.get("HTTP_REFERER", f"/events/{event.id}/#attendance"))


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "operations/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 25

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user_notifs = Notification.objects.filter(recipient=self.request.user)
        ctx["unread_count"] = user_notifs.filter(is_read=False).count()
        ctx["total_count"] = user_notifs.count()
        return ctx


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok", "unread_count": 0})
        messages.success(request, "All notifications marked as read.")
        return redirect(request.META.get("HTTP_REFERER", "notifications"))


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
            return JsonResponse({"status": "ok", "unread_count": unread})
        return redirect(notif.link or request.META.get("HTTP_REFERER", "notifications"))





