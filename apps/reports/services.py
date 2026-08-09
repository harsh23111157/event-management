"""ReportService — all report data computed from real database queries."""
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.events.models import Event, EventStatus
from apps.finance.models import Expense, ExpenseStatus
from apps.operations.models import Attendance, EventTask, TaskStatus
from apps.vendors.models import EventVendor, Vendor


class ReportService:
    @staticmethod
    def event_status_report():
        return Event.objects.aggregate(
            total=Count("id"),
            draft=Count("id", filter=Q(status=EventStatus.DRAFT)),
            submitted=Count("id", filter=Q(status=EventStatus.SUBMITTED)),
            approved=Count("id", filter=Q(status=EventStatus.APPROVED)),
            in_progress=Count("id", filter=Q(status=EventStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=EventStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=EventStatus.CANCELLED)),
            rejected=Count("id", filter=Q(status=EventStatus.REJECTED)),
        )

    @staticmethod
    def finance_report():
        approved = Expense.objects.filter(status=ExpenseStatus.APPROVED).aggregate(
            total=Coalesce(Sum("amount"), 0)
        )["total"]
        pending = Expense.objects.filter(status=ExpenseStatus.PENDING).aggregate(
            total=Coalesce(Sum("amount"), 0), count=Count("id")
        )
        rejected = Expense.objects.filter(status=ExpenseStatus.REJECTED).aggregate(
            total=Coalesce(Sum("amount"), 0), count=Count("id")
        )
        total_budget = Event.objects.exclude(status=EventStatus.CANCELLED).aggregate(
            b=Coalesce(Sum("budget"), 0)
        )["b"]
        remaining = total_budget - approved
        utilization = (float(approved) / float(total_budget) * 100) if total_budget else 0
        return {
            "total_budget": total_budget,
            "approved_expenses": approved,
            "pending_expenses": pending["total"],
            "pending_count": pending["count"],
            "rejected_expenses": rejected["total"],
            "rejected_count": rejected["count"],
            "remaining_budget": remaining,
            "utilization_pct": round(utilization, 1),
        }

    @staticmethod
    def task_report():
        from django.utils import timezone
        now = timezone.now()
        return EventTask.objects.aggregate(
            total=Count("id"),
            todo=Count("id", filter=Q(status=TaskStatus.TODO)),
            in_progress=Count("id", filter=Q(status=TaskStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            blocked=Count("id", filter=Q(status=TaskStatus.BLOCKED)),
            overdue=Count("id", filter=~Q(status=TaskStatus.COMPLETED) & Q(due_date__lt=now)),
        )

    @staticmethod
    def vendor_report():
        total_vendors = Vendor.objects.aggregate(c=Count("id"))["c"]
        active_vendors = Vendor.objects.filter(is_active=True).aggregate(c=Count("id"))["c"]
        assignments = EventVendor.objects.aggregate(
            total=Count("id"),
            planned=Count("id", filter=Q(status="PLANNED")),
            confirmed=Count("id", filter=Q(status="CONFIRMED")),
            completed=Count("id", filter=Q(status="COMPLETED")),
            cancelled=Count("id", filter=Q(status="CANCELLED")),
            total_value=Coalesce(Sum("contract_amount"), 0),
        )
        return {"total_vendors": total_vendors, "active_vendors": active_vendors, **assignments}

    @staticmethod
    def attendance_report():
        return Attendance.objects.aggregate(
            total=Count("id"),
            present=Count("id", filter=Q(status="PRESENT")),
            absent=Count("id", filter=Q(status="ABSENT")),
            late=Count("id", filter=Q(status="LATE")),
        )
