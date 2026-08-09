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
    def _verify_manager_or_admin(event: Event, user):
        if user.is_admin:
            return
        if user.is_event_manager and event.manager_id == user.id:
            return
        raise PermissionError("You can only perform workflow actions on events you manage.")

    @staticmethod
    @transaction.atomic
    def submit_event(event: Event, user) -> Event:
        EventWorkflowService._verify_manager_or_admin(event, user)
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
        EventWorkflowService._verify_manager_or_admin(event, user)
        if event.status not in (EventStatus.SUBMITTED, EventStatus.REJECTED):
            raise ValueError("Only submitted or rejected events can be returned to draft.")
        event.status = EventStatus.DRAFT
        event.save()
        AuditService.log(user, "EVENT_RETURN_DRAFT", "event", event.id, f"Returned event '{event.name}' to draft")
        return event

    @staticmethod
    @transaction.atomic
    def start_event(event: Event, user) -> Event:
        EventWorkflowService._verify_manager_or_admin(event, user)
        if event.status != EventStatus.APPROVED:
            raise ValueError("Only approved events can be started.")
        event.status = EventStatus.IN_PROGRESS
        event.save()
        AuditService.log(user, "EVENT_START", "event", event.id, f"Started event '{event.name}'")
        return event

    @staticmethod
    @transaction.atomic
    def complete_event(event: Event, user) -> Event:
        EventWorkflowService._verify_manager_or_admin(event, user)
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
        EventWorkflowService._verify_manager_or_admin(event, user)
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


class EventReadinessService:
    """Deterministic calculation of event operational readiness."""

    @staticmethod
    def calculate_readiness(event: Event) -> dict:
        checklist = []

        # 1. Venue & Capacity
        has_venue = bool(event.venue_id)
        cap_ok = bool(has_venue and event.expected_attendees <= event.venue.capacity)
        checklist.append({
            "name": "Venue Capacity",
            "passed": has_venue and cap_ok,
            "required": True,
            "detail": f"{event.venue.name} (Cap: {event.venue.capacity}, Expected: {event.expected_attendees})" if has_venue else "No venue assigned",
        })

        # 2. Manager
        has_mgr = bool(event.manager_id)
        checklist.append({
            "name": "Assigned Manager",
            "passed": has_mgr,
            "required": True,
            "detail": f"{event.manager.get_full_name() or event.manager.username}" if has_mgr else "No manager assigned",
        })

        # 3. Budget
        has_budget = bool(event.budget and event.budget > 0)
        checklist.append({
            "name": "Budget Allocated",
            "passed": has_budget,
            "required": True,
            "detail": f"₹{float(event.budget):,.0f}" if has_budget else "No budget allocated",
        })

        # 4. Staff Team
        staff_count = event.staff_assignments.count()
        checklist.append({
            "name": "Staff Team Assigned",
            "passed": staff_count >= 1,
            "required": True,
            "detail": f"{staff_count} staff assigned" if staff_count else "Zero staff assigned",
        })

        # 5. Tasks
        task_count = event.tasks.count()
        checklist.append({
            "name": "Operational Tasks",
            "passed": task_count >= 1,
            "required": True,
            "detail": f"{task_count} tasks created" if task_count else "Zero tasks defined",
        })

        # 6. Critical Tasks
        critical_uncompleted = event.tasks.filter(priority="CRITICAL").exclude(status="COMPLETED").count()
        checklist.append({
            "name": "Critical Tasks Resolution",
            "passed": critical_uncompleted == 0,
            "required": False,
            "detail": "All critical tasks completed" if critical_uncompleted == 0 else f"{critical_uncompleted} critical tasks pending",
        })

        # 7. Schedule
        schedule_count = event.schedules.count()
        checklist.append({
            "name": "Schedule & Agenda",
            "passed": schedule_count >= 1,
            "required": False,
            "detail": f"{schedule_count} schedule items" if schedule_count else "No schedule defined",
        })

        # 8. Vendors
        vendor_count = event.vendor_assignments.count()
        checklist.append({
            "name": "Vendor Coordination",
            "passed": vendor_count >= 1,
            "required": False,
            "detail": f"{vendor_count} vendors contracted" if vendor_count else "No vendors assigned",
        })

        passed_count = sum(1 for item in checklist if item["passed"])
        total_count = len(checklist)
        score = int(round((passed_count / total_count) * 100))

        critical_failed = not (has_venue and cap_ok and has_mgr and has_budget)
        if critical_failed or score < 50:
            readiness_status = "BLOCKED"
            badge_class = "danger"
        elif score < 80 or not (staff_count >= 1 and task_count >= 1):
            readiness_status = "NEEDS ATTENTION"
            badge_class = "warn"
        else:
            readiness_status = "READY"
            badge_class = "success"

        return {
            "score": score,
            "status": readiness_status,
            "badge_class": badge_class,
            "checklist": checklist,
            "passed_count": passed_count,
            "total_count": total_count,
        }
