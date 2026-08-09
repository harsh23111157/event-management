"""DashboardService — aggregates real statistics from the database."""
from collections import OrderedDict
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.events.models import Event, EventStatus
from apps.finance.models import Expense, ExpenseStatus
from apps.operations.models import EventTask, TaskStatus
from apps.vendors.models import Vendor


class DashboardService:
    """All numbers here are computed live from PostgreSQL — nothing is hardcoded."""

    @staticmethod
    def event_counts():
        qs = Event.objects.aggregate(
            total=Count("id"),
            draft=Count("id", filter=Q(status=EventStatus.DRAFT)),
            submitted=Count("id", filter=Q(status=EventStatus.SUBMITTED)),
            approved=Count("id", filter=Q(status=EventStatus.APPROVED)),
            in_progress=Count("id", filter=Q(status=EventStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=EventStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=EventStatus.CANCELLED)),
        )
        return qs

    @staticmethod
    def task_counts():
        now = timezone.now()
        qs = EventTask.objects.aggregate(
            total=Count("id"),
            todo=Count("id", filter=Q(status=TaskStatus.TODO)),
            in_progress=Count("id", filter=Q(status=TaskStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            blocked=Count("id", filter=Q(status=TaskStatus.BLOCKED)),
            overdue=Count("id", filter=~Q(status=TaskStatus.COMPLETED) & Q(due_date__lt=now)),
            critical_open=Count("id", filter=Q(priority="CRITICAL") & ~Q(status=TaskStatus.COMPLETED)),
        )
        return qs

    @staticmethod
    def finance_totals():
        totals = Expense.objects.aggregate(
            approved_amount=Coalesce(Sum("amount", filter=Q(status=ExpenseStatus.APPROVED)), 0),
            pending_count=Count("id", filter=Q(status=ExpenseStatus.PENDING)),
        )
        total_budget = Event.objects.exclude(status=EventStatus.CANCELLED).aggregate(
            b=Coalesce(Sum("budget"), 0)
        )["b"]
        approved_expenses = totals["approved_amount"] or 0
        remaining = total_budget - approved_expenses
        utilization = (approved_expenses / total_budget * 100) if total_budget else 0
        return {
            "total_budget": total_budget,
            "approved_expenses": approved_expenses,
            "remaining_budget": remaining,
            "utilization_pct": round(utilization, 1),
            "pending_approvals": totals["pending_count"],
        }

    @staticmethod
    def upcoming_events(limit=5):
        now = timezone.now()
        return (Event.objects.filter(start_date__gte=now)
                .exclude(status=EventStatus.CANCELLED)
                .order_by("start_date")[:limit])

    @staticmethod
    def critical_tasks(limit=5):
        return (EventTask.objects.filter(priority="CRITICAL")
                .exclude(status=TaskStatus.COMPLETED)
                .select_related("event", "assigned_to")
                .order_by("due_date")[:limit])

    @staticmethod
    def overdue_tasks(limit=5):
        now = timezone.now()
        return (EventTask.objects.exclude(status=TaskStatus.COMPLETED)
                .filter(due_date__lt=now)
                .select_related("event", "assigned_to")
                .order_by("due_date")[:limit])

    @staticmethod
    def pending_approvals(limit=5):
        return (Event.objects.filter(status=EventStatus.SUBMITTED)
                .select_related("manager", "venue")
                .order_by("updated_at")[:limit])

    @staticmethod
    def recent_activity(limit=8):
        from apps.audit.models import AuditLog
        return (AuditLog.objects.select_related("user")
                .order_by("-timestamp")[:limit])

    @staticmethod
    def staff_assignments():
        from apps.operations.models import EventStaff
        return EventStaff.objects.aggregate(total=Count("id"))["total"]

    @staticmethod
    def vendor_count():
        return Vendor.objects.aggregate(active=Count("id", filter=Q(is_active=True)))["active"]

    @staticmethod
    def budget_warnings():
        from django.conf import settings
        fin = DashboardService.finance_totals()
        warnings = []
        if fin["total_budget"] > 0:
            if fin["utilization_pct"] >= getattr(settings, "BUDGET_CRITICAL_THRESHOLD", 90):
                warnings.append(("danger", f"Budget utilization critical at {fin['utilization_pct']}%"))
            elif fin["utilization_pct"] >= getattr(settings, "BUDGET_WARN_THRESHOLD", 80):
                warnings.append(("warning", f"Budget utilization high at {fin['utilization_pct']}%"))
        return warnings

    @staticmethod
    def full_context():
        ev = DashboardService.event_counts()
        tk = DashboardService.task_counts()
        fin = DashboardService.finance_totals()
        return {
            "events": ev,
            "tasks": tk,
            "finance": fin,
            "upcoming_events": list(DashboardService.upcoming_events()),
            "critical_tasks": list(DashboardService.critical_tasks()),
            "overdue_tasks": list(DashboardService.overdue_tasks()),
            "pending_approvals": list(DashboardService.pending_approvals()),
            "recent_activity": list(DashboardService.recent_activity()),
            "staff_assignments": DashboardService.staff_assignments(),
            "vendor_count": DashboardService.vendor_count(),
            "budget_warnings": DashboardService.budget_warnings(),
        }
