from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.accounts.models import Role
from apps.events.models import Event
from apps.operations.models import (
    Attendance, AttendanceStatus, EventStaff, EventTask,
    NotificationService, NotificationType, Schedule, TaskPriority, TaskStatus
)

User = get_user_model()


class EventTaskForm(forms.ModelForm):
    title = forms.CharField(
        min_length=3,
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Set up main audio equipment", "required": "required"}),
        error_messages={"required": "Task title is required.", "min_length": "Task title must be at least 3 characters."}
    )
    due_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "required": "required"}, format="%Y-%m-%dT%H:%M"),
        error_messages={"required": "Due date and time is required."}
    )

    class Meta:
        model = EventTask
        fields = ["event", "title", "description", "assigned_to", "due_date", "priority", "status", "notes"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Detailed instructions and operational checklist..."}),
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": "Execution notes, blockers, or deliverables..."}),
        }

    def __init__(self, *args, event=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.user = user

        # If event is pre-scoped, hide the event field
        if event or (self.instance and self.instance.pk and self.instance.event_id):
            if "event" in self.fields:
                self.fields["event"].required = False
                self.fields["event"].widget = forms.HiddenInput()
                self.fields["event"].initial = event or self.instance.event
        else:
            if "event" in self.fields:
                self.fields["event"].required = True
                event_qs = Event.objects.exclude(status="CANCELLED")
                if user and user.is_event_manager:
                    event_qs = event_qs.filter(manager=user)
                self.fields["event"].queryset = event_qs
                self.fields["event"].empty_label = "— Select an Event —"

        # Apply CSS form classes
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")

        # Allow selecting from all active staff and event managers/admins
        staff_qs = User.objects.filter(is_active=True).filter(
            Q(role=Role.STAFF) | Q(role=Role.EVENT_MANAGER) | Q(role=Role.ADMIN)
        ).order_by("role", "first_name", "last_name")
        self.fields["assigned_to"].queryset = staff_qs
        self.fields["assigned_to"].empty_label = "— Select Staff Member (Optional) —"

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title or len(title) < 3:
            raise ValidationError("Task title must be at least 3 characters.")
        return title

    def clean(self):
        cleaned = super().clean()
        target_event = self.event or cleaned.get("event") or (self.instance and self.instance.event if self.instance.pk else None)
        if not target_event:
            self.add_error("event", "An event must be selected for this task.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.event:
            instance.event = self.event

        if commit:
            instance.save()
            # If a staff member is assigned, ensure they are enrolled in the event staff team
            if instance.assigned_to and instance.event:
                EventStaff.objects.get_or_create(
                    event=instance.event,
                    staff=instance.assigned_to,
                    defaults={"role": "Task Assignee"}
                )
                # Send notification to the assigned staff member
                due_formatted = instance.due_date.strftime("%b %d, %Y at %H:%M") if instance.due_date else "Not set"
                NotificationService.send(
                    recipient=instance.assigned_to,
                    title=f"New Task Assigned: {instance.title}",
                    message=f"You have been assigned to task '{instance.title}' for event '{instance.event.name}'. Due: {due_formatted}. Priority: {instance.get_priority_display()}.",
                    notification_type=NotificationType.TASK_ASSIGNED,
                    link=f"/tasks/{instance.id}/edit/",
                )
        return instance


class StaffTaskUpdateForm(forms.ModelForm):
    """Staff can update status and operational notes on their assigned tasks."""
    status = forms.ChoiceField(
        choices=TaskStatus.choices,
        required=True,
        error_messages={"required": "Please select a task status."}
    )

    class Meta:
        model = EventTask
        fields = ["status", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Add task execution notes, progress report, or blockers..."}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit and instance.event and instance.event.manager:
            # Notify event manager of status update
            updater_name = self.user.get_full_name() if self.user else "Assigned Staff"
            NotificationService.send(
                recipient=instance.event.manager,
                title=f"Task Progress Updated: {instance.title}",
                message=f"{updater_name} updated task '{instance.title}' to status '{instance.get_status_display()}'. Notes: {instance.notes or 'None'}",
                notification_type=NotificationType.TASK_UPDATED,
                link=f"/events/{instance.event.id}/#tasks",
            )
        return instance


class EventStaffForm(forms.ModelForm):
    role = forms.CharField(
        min_length=2,
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Stage Manager, Security Lead, Registration Desk", "required": "required"}),
        error_messages={"required": "Staff role / responsibility is required.", "min_length": "Role description must be at least 2 characters."}
    )

    class Meta:
        model = EventStaff
        fields = ["staff", "role"]

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["staff"].queryset = User.objects.filter(is_active=True).filter(
            Q(role=Role.STAFF) | Q(role=Role.EVENT_MANAGER) | Q(role=Role.ADMIN)
        ).order_by("role", "first_name", "last_name")
        self.fields["staff"].empty_label = "— Select Staff Member —"
        self.fields["staff"].required = True

        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")

    def clean_role(self):
        role = self.cleaned_data.get("role", "").strip()
        if not role or len(role) < 2:
            raise ValidationError("Role description must be at least 2 characters.")
        return role

    def clean(self):
        cleaned = super().clean()
        staff = cleaned.get("staff")
        if staff and self.event:
            qs = EventStaff.objects.filter(event=self.event, staff=staff)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("staff", f"{staff.get_full_name() or staff.username} is already assigned to this event.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.event:
            instance.event = self.event
        if commit:
            instance.save()
            NotificationService.send(
                recipient=instance.staff,
                title=f"Assigned to Event: {instance.event.name}",
                message=f"You have been assigned to event '{instance.event.name}' as '{instance.role}'.",
                notification_type=NotificationType.EVENT_ASSIGNED,
                link=f"/events/{instance.event.id}/",
            )
        return instance


class ScheduleForm(forms.ModelForm):
    title = forms.CharField(
        min_length=2,
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Keynote Speech, Lunch Break", "required": "required"}),
        error_messages={"required": "Session title is required."}
    )
    start_time = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "required": "required"}, format="%Y-%m-%dT%H:%M"),
        error_messages={"required": "Start time is required."}
    )
    end_time = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "required": "required"}, format="%Y-%m-%dT%H:%M"),
        error_messages={"required": "End time is required."}
    )

    class Meta:
        model = Schedule
        fields = ["title", "description", "start_time", "end_time", "location", "responsible_staff"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Session overview, speaker names, requirements..."}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Main Auditorium, Hall B"}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")
        if event:
            self.fields["responsible_staff"].queryset = event.staff_assignments.select_related("staff").all()
            self.fields["responsible_staff"].empty_label = "— Lead Staff (Optional) —"

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title or len(title) < 2:
            raise ValidationError("Session title must be at least 2 characters.")
        return title

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "End time must be after start time.")
        if self.event and start and self.event.start_date and start < self.event.start_date:
            self.add_error("start_time", f"Schedule start ({start.strftime('%b %d %H:%M')}) is before event start ({self.event.start_date.strftime('%b %d %H:%M')}).")
        if self.event and end and self.event.end_date and end > self.event.end_date:
            self.add_error("end_time", f"Schedule end ({end.strftime('%b %d %H:%M')}) is after event end ({self.event.end_date.strftime('%b %d %H:%M')}).")
        return cleaned


class ManagerAttendanceForm(forms.ModelForm):
    """Allows Event Managers and Admins to record or update attendance for staff."""
    status = forms.ChoiceField(
        choices=AttendanceStatus.choices,
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={"required": "Attendance status is required."}
    )
    check_in = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}, format="%Y-%m-%dT%H:%M"),
        help_text="Leave blank to use current timestamp"
    )
    check_out = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}, format="%Y-%m-%dT%H:%M"),
    )

    class Meta:
        model = Attendance
        fields = ["staff", "status", "check_in", "check_out"]

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")

        if event:
            # Query all staff assigned to this event
            assigned_user_ids = event.staff_assignments.values_list("staff_id", flat=True)
            self.fields["staff"].queryset = User.objects.filter(id__in=assigned_user_ids).order_by("first_name")
            self.fields["staff"].empty_label = "— Select Assigned Staff Member —"

    def clean(self):
        cleaned = super().clean()
        in_time = cleaned.get("check_in")
        out_time = cleaned.get("check_out")
        if in_time and out_time and out_time <= in_time:
            self.add_error("check_out", "Check-out time must be after check-in time.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.event:
            instance.event = self.event
        if commit:
            instance.save()
        return instance

