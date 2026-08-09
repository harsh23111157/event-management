"""Event model and workflow status choices."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.venues.models import Venue


class EventType(models.TextChoices):
    CONFERENCE = "CONFERENCE", "Conference"
    HACKATHON = "HACKATHON", "Hackathon"
    WORKSHOP = "WORKSHOP", "Workshop"
    MEETUP = "MEETUP", "Meetup"
    SPORTS = "SPORTS", "Sports"
    OTHER = "OTHER", "Other"


class EventStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    REJECTED = "REJECTED", "Rejected"


class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.OTHER)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name="managed_events")
    expected_attendees = models.PositiveIntegerField(default=0)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.DRAFT)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(condition=models.Q(budget__gte=0), name="event_budget_nonneg"),
            models.CheckConstraint(condition=models.Q(expected_attendees__gte=0), name="event_attendees_nonneg"),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError({"end_date": "End date must be after start date."})
        if self.budget is not None and self.budget <= 0:
            raise ValidationError({"budget": "Budget must be greater than zero."})
        if self.venue_id and self.expected_attendees and self.expected_attendees > self.venue.capacity:
            raise ValidationError({"expected_attendees": "Expected attendees exceed venue capacity."})

    @property
    def is_editable(self) -> bool:
        return self.status in (EventStatus.DRAFT, EventStatus.SUBMITTED, EventStatus.REJECTED)
