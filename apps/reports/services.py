from decimal import Decimal
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.events.models import Event, EventStatus
from apps.finance.models import Expense, ExpenseCategory, ExpenseStatus
from apps.operations.models import Attendance, EventStaff, EventTask, TaskPriority, TaskStatus
from apps.vendors.models import EventVendor, Vendor


class ReportService:
    """Aggregates real report data scoped strictly by role permissions."""

    @staticmethod
    def _scope_events(user):
        qs = Event.objects.all()
        if user and user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=user).distinct()
        elif user and user.is_event_manager:
            qs = qs.filter(manager=user)
        return qs

    @staticmethod
    def event_status_report(user=None):
        qs = ReportService._scope_events(user)
        return qs.aggregate(
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
    def finance_report(user=None):
        exp_qs = Expense.objects.all()
        ev_qs = Event.objects.exclude(status=EventStatus.CANCELLED)

        if user and user.is_event_manager:
            exp_qs = exp_qs.filter(event__manager=user)
            ev_qs = ev_qs.filter(manager=user)
        elif user and user.is_staff_member:
            exp_qs = exp_qs.filter(event__staff_assignments__staff=user).distinct()
            ev_qs = ev_qs.filter(staff_assignments__staff=user).distinct()

        approved = exp_qs.filter(status=ExpenseStatus.APPROVED).aggregate(
            total=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField())
        )["total"]
        pending = exp_qs.filter(status=ExpenseStatus.PENDING).aggregate(
            total=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField()), count=Count("id")
        )
        rejected = exp_qs.filter(status=ExpenseStatus.REJECTED).aggregate(
            total=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField()), count=Count("id")
        )
        total_budget = ev_qs.aggregate(
            b=Coalesce(Sum("budget"), Decimal(0), output_field=DecimalField())
        )["b"]
        remaining = total_budget - approved
        utilization = (float(approved) / float(total_budget) * 100) if total_budget and float(total_budget) > 0 else 0.0

        # Category breakdown
        category_breakdown = list(
            exp_qs.filter(status=ExpenseStatus.APPROVED)
            .values("category")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        return {
            "total_budget": total_budget,
            "approved_expenses": approved,
            "pending_expenses": pending["total"],
            "pending_count": pending["count"],
            "rejected_expenses": rejected["total"],
            "rejected_count": rejected["count"],
            "remaining_budget": remaining,
            "utilization_pct": round(utilization, 1),
            "categories": category_breakdown,
        }

    @staticmethod
    def task_report(user=None):
        now = timezone.now()
        qs = EventTask.objects.all()
        if user and user.is_staff_member:
            qs = qs.filter(assigned_to=user)
        elif user and user.is_event_manager:
            qs = qs.filter(event__manager=user)

        return qs.aggregate(
            total=Count("id"),
            todo=Count("id", filter=Q(status=TaskStatus.TODO)),
            in_progress=Count("id", filter=Q(status=TaskStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            blocked=Count("id", filter=Q(status=TaskStatus.BLOCKED)),
            overdue=Count("id", filter=~Q(status=TaskStatus.COMPLETED) & Q(due_date__lt=now)),
            critical=Count("id", filter=Q(priority=TaskPriority.CRITICAL)),
        )

    @staticmethod
    def vendor_report(user=None):
        ev_vendors = EventVendor.objects.select_related("vendor", "event")
        if user and user.is_event_manager:
            ev_vendors = ev_vendors.filter(event__manager=user)

        total_vendors = Vendor.objects.aggregate(c=Count("id"))["c"]
        active_vendors = Vendor.objects.filter(is_active=True).aggregate(c=Count("id"))["c"]
        assignments = ev_vendors.aggregate(
            total=Count("id"),
            planned=Count("id", filter=Q(status="PLANNED")),
            confirmed=Count("id", filter=Q(status="CONFIRMED")),
            completed=Count("id", filter=Q(status="COMPLETED")),
            cancelled=Count("id", filter=Q(status="CANCELLED")),
            total_value=Coalesce(Sum("contract_amount"), Decimal(0), output_field=DecimalField()),
        )
        return {"total_vendors": total_vendors, "active_vendors": active_vendors, **assignments}

    @staticmethod
    def attendance_report(user=None):
        qs = Attendance.objects.all()
        if user and user.is_staff_member:
            qs = qs.filter(staff=user)
        elif user and user.is_event_manager:
            qs = qs.filter(event__manager=user)

        return qs.aggregate(
            total=Count("id"),
            present=Count("id", filter=Q(status="PRESENT")),
            absent=Count("id", filter=Q(status="ABSENT")),
            late=Count("id", filter=Q(status="LATE")),
        )

    @staticmethod
    def staff_work_report(user):
        now = timezone.now()
        tasks = EventTask.objects.filter(assigned_to=user)
        assignments = EventStaff.objects.filter(staff=user).select_related("event")
        attendances = Attendance.objects.filter(staff=user)

        return {
            "total_tasks": tasks.count(),
            "completed_tasks": tasks.filter(status=TaskStatus.COMPLETED).count(),
            "in_progress_tasks": tasks.filter(status=TaskStatus.IN_PROGRESS).count(),
            "overdue_tasks": tasks.exclude(status=TaskStatus.COMPLETED).filter(due_date__lt=now).count(),
            "assigned_events_count": assignments.count(),
            "total_attendances": attendances.count(),
            "present_count": attendances.filter(status="PRESENT").count(),
        }

