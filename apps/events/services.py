"""EventWorkflowService — state machine for event lifecycle transitions."""
from django.db import transaction
from django.utils import timezone

from apps.accounts.permissions import is_admin, is_event_manager_or_admin
from apps.audit.services import AuditService
from apps.events.models import Event, EventStatus
from apps.events.validators import EventValidationService


class EventWorkflowService:
    """All transitions validate permissions, state, and business rules atomically."""

    @staticmethod
    @transaction.atomic
    def submit_event(event: Event, user) -> Event:
        if not is_event_manager_or_admin(user):
            raise PermissionError("Only event managers or admins can submit events.")
        errors = EventValidationService.validate_for_submission(event)
        conflict = EventValidationService.validate_venue_conflict(event)
        if conflict:
            errors.append(conflict)
        if errors:
            raise ValueError("Event validation failed: " + " | ".join(errors))
        event.status = EventStatus.SUBMITTED
        event.rejection_reason = ""
        event.save()
        AuditService.log(user, "EVENT_SUBMIT", "event", event.id, f"Submitted event '{event.name}'")
        return event

    @staticmethod
    @transaction.atomic
    def approve_event(event: Event, user) -> Event:
        if not is_admin(user):
            raise PermissionError("Only admins can approve events.")
        errors = EventValidationService.validate_for_approval(event)
        if errors:
            raise ValueError("Cannot approve event: " + " | ".join(errors))
        event.status = EventStatus.APPROVED
        event.rejection_reason = ""
        event.save()
        AuditService.log(user, "EVENT_APPROVE", "event", event.id, f"Approved event '{event.name}'")
        return event

    @staticmethod
    @transaction.atomic
    def reject_event(event: Event, user, reason: str) -> Event:
        if not is_admin(user):
            raise PermissionError("Only admins can reject events.")
        if not reason or not reason.strip():
            raise ValueError("A rejection reason is required.")
        if event.status != EventStatus.SUBMITTED:
            raise ValueError("Only submitted events can be rejected.")
        event.status = EventStatus.REJECTED
        event.rejection_reason = reason.strip()
        event.save()
        AuditService.log(user, "EVENT_REJECT", "event", event.id, f"Rejected event '{event.name}': {reason}")
        return event

    @staticmethod
    @transaction.atomic
    def return_to_draft(event: Event, user) -> Event:
        if not is_event_manager_or_admin(user):
            raise PermissionError("Only event managers or admins can return events to draft.")
        if event.status not in (EventStatus.SUBMITTED, EventStatus.REJECTED):
            raise ValueError("Only submitted or rejected events can be returned to draft.")
        event.status = EventStatus.DRAFT
        event.save()
        AuditService.log(user, "EVENT_RETURN_DRAFT", "event", event.id, f"Returned event '{event.name}' to draft")
        return event

    @staticmethod
    @transaction.atomic
    def start_event(event: Event, user) -> Event:
        if not is_event_manager_or_admin(user):
            raise PermissionError("Only event managers or admins can start events.")
        if event.status != EventStatus.APPROVED:
            raise ValueError("Only approved events can be started.")
        event.status = EventStatus.IN_PROGRESS
        event.save()
        AuditService.log(user, "EVENT_START", "event", event.id, f"Started event '{event.name}'")
        return event

    @staticmethod
    @transaction.atomic
    def complete_event(event: Event, user) -> Event:
        if not is_event_manager_or_admin(user):
            raise PermissionError("Only event managers or admins can complete events.")
        errors = EventValidationService.validate_for_completion(event)
        if errors:
            raise ValueError("Cannot complete event: " + " | ".join(errors))
        event.status = EventStatus.COMPLETED
        event.save()
        AuditService.log(user, "EVENT_COMPLETE", "event", event.id, f"Completed event '{event.name}'")
        return event

    @staticmethod
    @transaction.atomic
    def cancel_event(event: Event, user) -> Event:
        if not is_event_manager_or_admin(user):
            raise PermissionError("Only event managers or admins can cancel events.")
        if event.status in (EventStatus.COMPLETED, EventStatus.CANCELLED):
            raise ValueError("Completed or cancelled events cannot be cancelled again.")
        event.status = EventStatus.CANCELLED
        event.save()
        AuditService.log(user, "EVENT_CANCEL", "event", event.id, f"Cancelled event '{event.name}'")
        return event

    # Map of valid forward transitions for reference / testing.
    TRANSITIONS = {
        EventStatus.DRAFT: {EventStatus.SUBMITTED, EventStatus.CANCELLED},
        EventStatus.SUBMITTED: {EventStatus.APPROVED, EventStatus.REJECTED, EventStatus.DRAFT, EventStatus.CANCELLED},
        EventStatus.REJECTED: {EventStatus.DRAFT, EventStatus.CANCELLED},
        EventStatus.APPROVED: {EventStatus.IN_PROGRESS, EventStatus.CANCELLED},
        EventStatus.IN_PROGRESS: {EventStatus.COMPLETED, EventStatus.CANCELLED},
        EventStatus.COMPLETED: set(),
        EventStatus.CANCELLED: set(),
    }
