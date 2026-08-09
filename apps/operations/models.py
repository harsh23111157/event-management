"""Operational models: staff assignments, tasks, schedules, attendance."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.events.models import Event


class EventStaff(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="staff_assignments")
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="event_assignments")
    role = models.CharField(max_length=100, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "staff")
        ordering = ["assigned_at"]

    def __str__(self) -> str:
        return f"{self.staff} @ {self.event}"


class TaskStatus(models.TextChoices):
    TODO = "TODO", "To Do"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    BLOCKED = "BLOCKED", "Blocked"


class TaskPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class EventTask(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="assigned_tasks")
    due_date = models.DateTimeField()
    priority = models.CharField(max_length=10, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.TODO)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["due_date"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["priority"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.event})"


class Schedule(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="schedules")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    responsible_staff = models.ForeignKey(EventStaff, on_delete=models.SET_NULL,
                                            null=True, blank=True, related_name="schedules")

    class Meta:
        ordering = ["start_time"]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "End time must be after start time."})
        if self.event_id and self.start_time and self.start_time < self.event.start_date:
            raise ValidationError({"start_time": "Schedule start is before the event start."})
        if self.event_id and self.end_time and self.end_time > self.event.end_date:
            raise ValidationError({"end_time": "Schedule end is after the event end."})

    def __str__(self) -> str:
        return f"{self.title} ({self.event})"


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LATE = "LATE", "Late"


class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendances")
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="attendances")
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)

    class Meta:
        unique_together = ("event", "staff")

    def __str__(self) -> str:
        return f"{self.staff} @ {self.event} ({self.status})"


class NotificationType(models.TextChoices):
    TASK_ASSIGNED = "TASK_ASSIGNED", "Task Assigned"
    TASK_UPDATED = "TASK_UPDATED", "Task Updated"
    EVENT_ASSIGNED = "EVENT_ASSIGNED", "Event Assigned"
    EVENT_STATUS = "EVENT_STATUS", "Event Status Change"
    EXPENSE = "EXPENSE", "Expense Update"
    ATTENDANCE = "ATTENDANCE", "Attendance Update"
    GENERAL = "GENERAL", "General Notification"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.GENERAL)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"]), models.Index(fields=["created_at"])]

    def __str__(self) -> str:
        return f"To {self.recipient}: {self.title} ({'Read' if self.is_read else 'Unread'})"


class NotificationService:
    @staticmethod
    def send(recipient, title: str, message: str, notification_type: str = NotificationType.GENERAL, link: str = ""):
        if not recipient:
            return None
        return Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link or "",
        )

