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
