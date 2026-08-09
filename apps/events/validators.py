"""Event-level business validation helpers."""
from django.core.exceptions import ValidationError

from apps.events.models import Event, EventStatus

class EventValidationService:
    @staticmethod
    def _validate_common(event: Event) -> list[str]:
        errors: list[str] = []
        if event.budget is None or event.budget <= 0:
            errors.append("Budget must be greater than zero.")
        if event.expected_attendees is None or event.expected_attendees <= 0:
            errors.append("Expected attendees must be set.")
        if event.venue_id and event.expected_attendees and event.expected_attendees > event.venue.capacity:
            errors.append("Expected attendees exceed venue capacity.")
        if event.end_date <= event.start_date:
            errors.append("End date must be after start date.")
        if not event.manager_id:
            errors.append("Event must have an assigned manager.")
        if not event.tasks.exists():
            errors.append("Event must have at least one task before submission.")
        return errors

    @staticmethod
    def validate_for_submission(event: Event) -> list[str]:
        """Return a list of human-readable validation errors. Empty means valid."""
        errors: list[str] = []
        if event.status != EventStatus.DRAFT:
            errors.append("Only draft events can be submitted.")
        errors.extend(EventValidationService._validate_common(event))
        return errors

    @staticmethod
    def validate_for_approval(event: Event) -> list[str]:
        errors: list[str] = []
        if event.status != EventStatus.SUBMITTED:
            errors.append("Only submitted events can be approved.")
        errors.extend(EventValidationService._validate_common(event))
        if not event.staff_assignments.exists():
            errors.append("Event must have at least one staff member assigned.")
        return errors

    @staticmethod
    def validate_venue_conflict(event: Event) -> str | None:
        """Return an error message if another non-cancelled event overlaps at the same venue."""
        qs = Event.objects.filter(
            venue=event.venue,
            start_date__lt=event.end_date,
            end_date__gt=event.start_date,
        ).exclude(status=EventStatus.CANCELLED).exclude(pk=event.pk)
        if qs.exists():
            return "Another event is already booked at this venue during the selected timeframe."
        return None

    @staticmethod
    def validate_for_completion(event: Event) -> list[str]:
        errors: list[str] = []
        if event.status != EventStatus.IN_PROGRESS:
            errors.append("Only in-progress events can be completed.")
        open_critical = event.tasks.filter(priority="CRITICAL").exclude(status="COMPLETED")
        if open_critical.exists():
            errors.append("All critical tasks must be completed before the event can be completed.")
        if not event.tasks.filter(status="COMPLETED").exists():
            errors.append("At least one task must be completed before the event can be completed.")
        return errors

    @staticmethod
    def validate_create(data: dict) -> list[str]:
        errors: list[str] = []
        if data.get("end_date") and data.get("start_date") and data["end_date"] <= data["start_date"]:
            errors.append("End date must be after start date.")
        if data.get("budget") is not None and data["budget"] <= 0:
            errors.append("Budget must be greater than zero.")
        if data.get("expected_attendees") and data.get("venue"):
            if data["expected_attendees"] > data["venue"].capacity:
                errors.append("Expected attendees exceed venue capacity.")
        return errors
