"""DashboardService — aggregates real statistics, role-specific metrics, and live chart datasets."""
import json
from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Avg, Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.events.models import Event, EventStatus, EventType
from apps.finance.models import Expense, ExpenseCategory, ExpenseStatus
from apps.operations.models import Attendance, AttendanceStatus, EventStaff, EventTask, Schedule, TaskPriority, TaskStatus
from apps.vendors.models import EventVendor, Vendor
from apps.venues.models import Venue


class DashboardService:
    """All metrics and chart data are computed dynamically from real PostgreSQL/SQLite DB records."""

    @staticmethod
    def _apply_event_filters(qs, filters=None):
        if not filters:
            return qs
        status_val = filters.get("status")
        if status_val:
            qs = qs.filter(status=status_val)
        type_val = filters.get("event_type")
        if type_val:
            qs = qs.filter(event_type=type_val)
        venue_val = filters.get("venue")
        if venue_val and str(venue_val).isdigit():
            qs = qs.filter(venue_id=int(venue_val))
        date_range = filters.get("date_range")
        now = timezone.now()
        if date_range == "30d":
            qs = qs.filter(start_date__gte=now - timedelta(days=30), start_date__lte=now + timedelta(days=60))
        elif date_range == "90d":
            qs = qs.filter(start_date__gte=now - timedelta(days=90), start_date__lte=now + timedelta(days=180))
        elif date_range == "year":
            qs = qs.filter(start_date__year=now.year)
        return qs

    # -------------------------------------------------------------
    # ADMIN DASHBOARD
    # -------------------------------------------------------------
    @staticmethod
    def get_admin_dashboard(filters=None):
        now = timezone.now()
        events_base = DashboardService._apply_event_filters(Event.objects.all(), filters)

        # Event metrics
        event_stats = events_base.aggregate(
            total=Count("id"),
            draft=Count("id", filter=Q(status=EventStatus.DRAFT)),
            submitted=Count("id", filter=Q(status=EventStatus.SUBMITTED)),
            approved=Count("id", filter=Q(status=EventStatus.APPROVED)),
            in_progress=Count("id", filter=Q(status=EventStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=EventStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=EventStatus.CANCELLED)),
            rejected=Count("id", filter=Q(status=EventStatus.REJECTED)),
        )

        upcoming_count = events_base.filter(start_date__gte=now).exclude(status=EventStatus.CANCELLED).count()

        # Finance metrics
        total_budget = events_base.exclude(status=EventStatus.CANCELLED).aggregate(
            b=Coalesce(Sum("budget"), Decimal(0), output_field=DecimalField())
        )["b"]
        approved_exp = Expense.objects.filter(status=ExpenseStatus.APPROVED).aggregate(
            s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField())
        )["s"]
        pending_exp_count = Expense.objects.filter(status=ExpenseStatus.PENDING).count()
        pending_exp_sum = Expense.objects.filter(status=ExpenseStatus.PENDING).aggregate(
            s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField())
        )["s"]
        remaining_budget = total_budget - approved_exp
        utilization_pct = round(float(approved_exp) / float(total_budget) * 100, 1) if total_budget and float(total_budget) > 0 else 0.0

        # Task metrics
        tasks_qs = EventTask.objects.all()
        task_stats = tasks_qs.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            in_progress=Count("id", filter=Q(status=TaskStatus.IN_PROGRESS)),
            todo=Count("id", filter=Q(status=TaskStatus.TODO)),
            blocked=Count("id", filter=Q(status=TaskStatus.BLOCKED)),
            overdue=Count("id", filter=~Q(status=TaskStatus.COMPLETED) & Q(due_date__lt=now)),
            critical_open=Count("id", filter=Q(priority=TaskPriority.CRITICAL) & ~Q(status=TaskStatus.COMPLETED)),
        )

        # Operational metrics
        active_staff_count = EventStaff.objects.values("staff").distinct().count()
        active_vendors_count = Vendor.objects.filter(is_active=True).count()

        # Actionable alerts
        alerts = []
        if event_stats["submitted"] > 0:
            alerts.append({"type": "info", "title": "Pending Event Approvals", "text": f"{event_stats['submitted']} event(s) awaiting administrative approval.", "url": "/events/?status=SUBMITTED"})
        if pending_exp_count > 0:
            alerts.append({"type": "warn", "title": "Pending Expenses", "text": f"{pending_exp_count} expense request(s) totaling ₹{pending_exp_sum:,.0f} need review.", "url": "/expenses/?status=PENDING"})
        if task_stats["overdue"] > 0:
            alerts.append({"type": "danger", "title": "Overdue Tasks", "text": f"{task_stats['overdue']} task(s) are past their due dates.", "url": "/operations/tasks/?status=TODO"})
        if task_stats["critical_open"] > 0:
            alerts.append({"type": "danger", "title": "Critical Tasks", "text": f"{task_stats['critical_open']} critical operational task(s) unresolved.", "url": "/operations/tasks/?priority=CRITICAL"})
        if utilization_pct >= 90:
            alerts.append({"type": "danger", "title": "Budget Alert", "text": f"Organization budget utilization has reached critical {utilization_pct}%.", "url": "/expenses/"})
        elif utilization_pct >= 80:
            alerts.append({"type": "warn", "title": "High Utilization", "text": f"Organization budget utilization is at {utilization_pct}%.", "url": "/expenses/"})

        # Lists
        upcoming_events = list(events_base.filter(start_date__gte=now).exclude(status=EventStatus.CANCELLED).select_related("venue", "manager").order_by("start_date")[:5])
        pending_approvals = list(Event.objects.filter(status=EventStatus.SUBMITTED).select_related("manager", "venue").order_by("updated_at")[:5])
        critical_tasks = list(EventTask.objects.filter(priority=TaskPriority.CRITICAL).exclude(status=TaskStatus.COMPLETED).select_related("event", "assigned_to").order_by("due_date")[:5])
        recent_activity = list(AuditLog.objects.select_related("user").order_by("-timestamp")[:8])

        # Charts data
        charts = {
            "status": {
                "labels": ["Draft", "Submitted", "Approved", "In Progress", "Completed", "Cancelled", "Rejected"],
                "data": [
                    event_stats["draft"], event_stats["submitted"], event_stats["approved"],
                    event_stats["in_progress"], event_stats["completed"], event_stats["cancelled"], event_stats["rejected"]
                ],
                "colors": ["#94a3b8", "#3b82f6", "#10b981", "#f59e0b", "#06b6d4", "#ef4444", "#dc2626"],
            },
            "monthly": DashboardService._build_monthly_events_chart(events_base),
            "budget": {
                "total": float(total_budget),
                "approved": float(approved_exp),
                "remaining": float(remaining_budget),
                "utilization": utilization_pct,
            },
            "tasks": {
                "labels": ["Completed", "In Progress", "To Do", "Blocked"],
                "data": [task_stats["completed"], task_stats["in_progress"], task_stats["todo"], task_stats["blocked"]],
                "colors": ["#10b981", "#f59e0b", "#94a3b8", "#ef4444"],
            },
            "event_types": DashboardService._build_event_types_chart(events_base),
            "venues": DashboardService._build_venue_utilization_chart(),
            "expense_categories": DashboardService._build_expense_categories_chart(),
        }

        return {
            "role": "ADMIN",
            "summary": {
                "total_events": event_stats["total"],
                "upcoming_events": upcoming_count,
                "in_progress_events": event_stats["in_progress"],
                "completed_events": event_stats["completed"],
                "total_budget": total_budget,
                "approved_expenses": approved_exp,
                "remaining_budget": remaining_budget,
                "utilization_pct": utilization_pct,
                "pending_event_approvals": event_stats["submitted"],
                "pending_expense_approvals": pending_exp_count,
                "overdue_tasks": task_stats["overdue"],
                "critical_tasks": task_stats["critical_open"],
                "active_staff": active_staff_count,
                "active_vendors": active_vendors_count,
            },
            "alerts": alerts,
            "charts_json": json.dumps(charts, default=str),
            "upcoming_events": upcoming_events,
            "pending_approvals": pending_approvals,
            "critical_tasks": critical_tasks,
            "recent_activity": recent_activity,
            "venues": Venue.objects.all(),
            "event_types": EventType.choices,
        }

    # -------------------------------------------------------------
    # EVENT MANAGER DASHBOARD
    # -------------------------------------------------------------
    @staticmethod
    def get_manager_dashboard(user, filters=None):
        now = timezone.now()
        events_base = DashboardService._apply_event_filters(Event.objects.filter(manager=user), filters)

        event_stats = events_base.aggregate(
            total=Count("id"),
            draft=Count("id", filter=Q(status=EventStatus.DRAFT)),
            submitted=Count("id", filter=Q(status=EventStatus.SUBMITTED)),
            approved=Count("id", filter=Q(status=EventStatus.APPROVED)),
            in_progress=Count("id", filter=Q(status=EventStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=EventStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=EventStatus.CANCELLED)),
            rejected=Count("id", filter=Q(status=EventStatus.REJECTED)),
        )

        upcoming_count = events_base.filter(start_date__gte=now).exclude(status=EventStatus.CANCELLED).count()

        # My events budget & expenses
        total_budget = events_base.exclude(status=EventStatus.CANCELLED).aggregate(
            b=Coalesce(Sum("budget"), Decimal(0), output_field=DecimalField())
        )["b"]
        approved_exp = Expense.objects.filter(event__manager=user, status=ExpenseStatus.APPROVED).aggregate(
            s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField())
        )["s"]
        pending_exp = Expense.objects.filter(event__manager=user, status=ExpenseStatus.PENDING).aggregate(
            s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField())
        )["s"]
        remaining_budget = total_budget - approved_exp
        utilization_pct = round(float(approved_exp) / float(total_budget) * 100, 1) if total_budget and float(total_budget) > 0 else 0.0

        # Tasks for managed events
        tasks_qs = EventTask.objects.filter(event__manager=user)
        task_stats = tasks_qs.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            in_progress=Count("id", filter=Q(status=TaskStatus.IN_PROGRESS)),
            todo=Count("id", filter=Q(status=TaskStatus.TODO)),
            blocked=Count("id", filter=Q(status=TaskStatus.BLOCKED)),
            overdue=Count("id", filter=~Q(status=TaskStatus.COMPLETED) & Q(due_date__lt=now)),
            critical_open=Count("id", filter=Q(priority=TaskPriority.CRITICAL) & ~Q(status=TaskStatus.COMPLETED)),
        )

        # Alerts for manager
        alerts = []
        if event_stats["rejected"] > 0:
            alerts.append({"type": "danger", "title": "Action Required", "text": f"{event_stats['rejected']} event(s) were returned/rejected by admin. Review and revise.", "url": "/events/?status=REJECTED"})
        if event_stats["draft"] > 0:
            alerts.append({"type": "info", "title": "Draft Events", "text": f"You have {event_stats['draft']} draft event(s) ready to be finalized and submitted.", "url": "/events/?status=DRAFT"})
        if task_stats["overdue"] > 0:
            alerts.append({"type": "warn", "title": "Overdue Tasks", "text": f"{task_stats['overdue']} task(s) in your events are overdue.", "url": "/operations/tasks/"})
        if task_stats["critical_open"] > 0:
            alerts.append({"type": "danger", "title": "Critical Tasks Pending", "text": f"{task_stats['critical_open']} critical task(s) unresolved.", "url": "/operations/tasks/?priority=CRITICAL"})

        upcoming_events = list(events_base.filter(start_date__gte=now).exclude(status=EventStatus.CANCELLED).select_related("venue").order_by("start_date")[:5])
        critical_tasks = list(tasks_qs.filter(priority=TaskPriority.CRITICAL).exclude(status=TaskStatus.COMPLETED).select_related("event", "assigned_to").order_by("due_date")[:5])
        overdue_tasks = list(tasks_qs.exclude(status=TaskStatus.COMPLETED).filter(due_date__lt=now).select_related("event", "assigned_to").order_by("due_date")[:5])
        recent_activity = list(AuditLog.objects.filter(entity_type="event", entity_id__in=events_base.values_list("id", flat=True)).select_related("user").order_by("-timestamp")[:6])

        charts = {
            "status": {
                "labels": ["Draft", "Submitted", "Approved", "In Progress", "Completed", "Rejected"],
                "data": [
                    event_stats["draft"], event_stats["submitted"], event_stats["approved"],
                    event_stats["in_progress"], event_stats["completed"], event_stats["rejected"]
                ],
                "colors": ["#94a3b8", "#3b82f6", "#10b981", "#f59e0b", "#06b6d4", "#dc2626"],
            },
            "tasks": {
                "labels": ["Completed", "In Progress", "To Do", "Blocked"],
                "data": [task_stats["completed"], task_stats["in_progress"], task_stats["todo"], task_stats["blocked"]],
                "colors": ["#10b981", "#f59e0b", "#94a3b8", "#ef4444"],
            },
            "budget": {
                "total": float(total_budget),
                "approved": float(approved_exp),
                "remaining": float(remaining_budget),
                "utilization": utilization_pct,
            },
            "monthly": DashboardService._build_monthly_events_chart(events_base),
        }

        return {
            "role": "EVENT_MANAGER",
            "manager_name": user.get_full_name() or user.username,
            "summary": {
                "total_events": event_stats["total"],
                "upcoming_events": upcoming_count,
                "in_progress_events": event_stats["in_progress"],
                "completed_events": event_stats["completed"],
                "draft_events": event_stats["draft"],
                "submitted_events": event_stats["submitted"],
                "total_budget": total_budget,
                "approved_expenses": approved_exp,
                "pending_expenses": pending_exp,
                "remaining_budget": remaining_budget,
                "utilization_pct": utilization_pct,
                "total_tasks": task_stats["total"],
                "completed_tasks": task_stats["completed"],
                "overdue_tasks": task_stats["overdue"],
                "critical_tasks": task_stats["critical_open"],
            },
            "alerts": alerts,
            "charts_json": json.dumps(charts, default=str),
            "upcoming_events": upcoming_events,
            "critical_tasks": critical_tasks,
            "overdue_tasks": overdue_tasks,
            "recent_activity": recent_activity,
            "venues": Venue.objects.all(),
            "event_types": EventType.choices,
        }

    # -------------------------------------------------------------
    # STAFF DASHBOARD
    # -------------------------------------------------------------
    @staticmethod
    def get_staff_dashboard(user, filters=None):
        now = timezone.now()
        my_tasks = EventTask.objects.filter(assigned_to=user).select_related("event", "event__venue")
        my_assignments = EventStaff.objects.filter(staff=user).select_related("event", "event__venue", "event__manager")
        assigned_events = Event.objects.filter(staff_assignments__staff=user).select_related("venue", "manager").distinct()

        task_stats = my_tasks.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            in_progress=Count("id", filter=Q(status=TaskStatus.IN_PROGRESS)),
            todo=Count("id", filter=Q(status=TaskStatus.TODO)),
            blocked=Count("id", filter=Q(status=TaskStatus.BLOCKED)),
            overdue=Count("id", filter=~Q(status=TaskStatus.COMPLETED) & Q(due_date__lt=now)),
            critical=Count("id", filter=Q(priority=TaskPriority.CRITICAL) & ~Q(status=TaskStatus.COMPLETED)),
        )

        today_tasks = list(my_tasks.exclude(status=TaskStatus.COMPLETED).order_by("priority", "due_date")[:8])
        upcoming_schedules = list(Schedule.objects.filter(event__in=assigned_events, start_time__gte=now).select_related("event").order_by("start_time")[:5])
        attendances = list(Attendance.objects.filter(staff=user).select_related("event").order_by("-check_in")[:5])

        # Active event attendance lookup
        active_attendance = {}
        for att in Attendance.objects.filter(staff=user, check_out__isnull=True):
            active_attendance[att.event_id] = att

        alerts = []
        if task_stats["overdue"] > 0:
            alerts.append({"type": "danger", "title": "Overdue Assignments", "text": f"You have {task_stats['overdue']} task(s) past the scheduled deadline.", "url": "/operations/tasks/"})
        if task_stats["critical"] > 0:
            alerts.append({"type": "warn", "title": "Critical Priority Tasks", "text": f"{task_stats['critical']} critical task(s) need immediate execution.", "url": "/operations/tasks/?priority=CRITICAL"})

        charts = {
            "tasks": {
                "labels": ["Completed", "In Progress", "To Do", "Blocked"],
                "data": [task_stats["completed"], task_stats["in_progress"], task_stats["todo"], task_stats["blocked"]],
                "colors": ["#10b981", "#f59e0b", "#94a3b8", "#ef4444"],
            },
            "priorities": {
                "labels": ["Critical", "High", "Medium", "Low"],
                "data": [
                    my_tasks.filter(priority=TaskPriority.CRITICAL).count(),
                    my_tasks.filter(priority=TaskPriority.HIGH).count(),
                    my_tasks.filter(priority=TaskPriority.MEDIUM).count(),
                    my_tasks.filter(priority=TaskPriority.LOW).count(),
                ],
                "colors": ["#ef4444", "#f59e0b", "#3b82f6", "#94a3b8"],
            }
        }

        return {
            "role": "STAFF",
            "staff_name": user.get_full_name() or user.username,
            "summary": {
                "assigned_events": assigned_events.count(),
                "pending_tasks": task_stats["todo"] + task_stats["in_progress"],
                "overdue_tasks": task_stats["overdue"],
                "completed_tasks": task_stats["completed"],
                "total_tasks": task_stats["total"],
                "critical_tasks": task_stats["critical"],
            },
            "alerts": alerts,
            "charts_json": json.dumps(charts, default=str),
            "today_tasks": today_tasks,
            "upcoming_schedules": upcoming_schedules,
            "my_assignments": my_assignments,
            "attendances": attendances,
            "active_attendance": active_attendance,
        }

    # -------------------------------------------------------------
    # FINANCE DASHBOARD
    # -------------------------------------------------------------
    @staticmethod
    def get_finance_dashboard(filters=None):
        events_base = DashboardService._apply_event_filters(Event.objects.exclude(status=EventStatus.CANCELLED), filters)

        total_budget = events_base.aggregate(b=Coalesce(Sum("budget"), Decimal(0), output_field=DecimalField()))["b"]
        approved_exp = Expense.objects.filter(status=ExpenseStatus.APPROVED).aggregate(s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField()))["s"]
        pending_exp_qs = Expense.objects.filter(status=ExpenseStatus.PENDING)
        pending_exp_count = pending_exp_qs.count()
        pending_exp_sum = pending_exp_qs.aggregate(s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField()))["s"]
        rejected_exp_sum = Expense.objects.filter(status=ExpenseStatus.REJECTED).aggregate(s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField()))["s"]
        remaining_budget = total_budget - approved_exp
        utilization_pct = round(float(approved_exp) / float(total_budget) * 100, 1) if total_budget and float(total_budget) > 0 else 0.0

        # Pending approval queue
        pending_approvals_queue = list(pending_exp_qs.select_related("event", "created_by", "event__manager").order_by("-created_at")[:10])

        # High utilization event alerts
        high_util_events = []
        for ev in Event.objects.exclude(status=EventStatus.CANCELLED).annotate(
            app_exp=Coalesce(Sum("expenses__amount", filter=Q(expenses__status=ExpenseStatus.APPROVED)), Decimal(0), output_field=DecimalField())
        ):
            b_val = float(ev.budget) if ev.budget else 0.0
            e_val = float(ev.app_exp)
            u_pct = round((e_val / b_val * 100), 1) if b_val > 0 else 0.0
            if u_pct >= 80:
                high_util_events.append({"event": ev, "budget": ev.budget, "spent": ev.app_exp, "utilization": u_pct})

        alerts = []
        if pending_exp_count > 0:
            alerts.append({"type": "warn", "title": "Approval Queue", "text": f"{pending_exp_count} expense request(s) totaling ₹{pending_exp_sum:,.0f} awaiting Finance approval.", "url": "/expenses/?status=PENDING"})
        if high_util_events:
            alerts.append({"type": "danger", "title": "Budget Watchlist", "text": f"{len(high_util_events)} event(s) have reached or exceeded 80% budget consumption.", "url": "/expenses/"})

        # Recent approved / rejected
        recent_expenses = list(Expense.objects.exclude(status=ExpenseStatus.PENDING).select_related("event", "approved_by", "created_by").order_by("-updated_at")[:6])

        # Vendor contracts breakdown
        top_vendors = list(Vendor.objects.annotate(total_contract=Coalesce(Sum("event_assignments__contract_amount"), Decimal(0), output_field=DecimalField())).order_by("-total_contract")[:6])

        charts = {
            "budget": {
                "total": float(total_budget),
                "approved": float(approved_exp),
                "pending": float(pending_exp_sum),
                "remaining": float(remaining_budget),
                "utilization": utilization_pct,
            },
            "monthly_expenses": DashboardService._build_monthly_expenses_chart(),
            "expense_categories": DashboardService._build_expense_categories_chart(),
            "event_spending": DashboardService._build_event_spending_chart(),
        }

        return {
            "role": "FINANCE",
            "summary": {
                "total_budget": total_budget,
                "approved_expenses": approved_exp,
                "pending_approvals_count": pending_exp_count,
                "pending_approvals_sum": pending_exp_sum,
                "rejected_expenses": rejected_exp_sum,
                "remaining_budget": remaining_budget,
                "utilization_pct": utilization_pct,
            },
            "alerts": alerts,
            "charts_json": json.dumps(charts, default=str),
            "pending_approvals_queue": pending_approvals_queue,
            "recent_expenses": recent_expenses,
            "high_util_events": high_util_events,
            "top_vendors": top_vendors,
            "venues": Venue.objects.all(),
            "event_types": EventType.choices,
        }

    # -------------------------------------------------------------
    # CHART BUILDERS
    # -------------------------------------------------------------
    @staticmethod
    def _build_monthly_events_chart(qs):
        months_data = OrderedDict()
        now = timezone.now()
        # Last 6 months up to next 6 months
        for m_offset in range(-5, 7):
            dt = now.replace(day=1) + timedelta(days=m_offset * 30)
            key = dt.strftime("%b %Y")
            months_data[key] = 0

        for item in qs.annotate(m=TruncMonth("start_date")).values("m").annotate(c=Count("id")).order_by("m"):
            if item["m"]:
                k = item["m"].strftime("%b %Y")
                if k in months_data:
                    months_data[k] = item["c"]

        return {
            "labels": list(months_data.keys()),
            "data": list(months_data.values()),
        }

    @staticmethod
    def _build_monthly_expenses_chart():
        months_data = OrderedDict()
        now = timezone.now()
        for m_offset in range(-5, 1):
            dt = now.replace(day=1) + timedelta(days=m_offset * 30)
            key = dt.strftime("%b %Y")
            months_data[key] = 0.0

        for item in Expense.objects.filter(status=ExpenseStatus.APPROVED).annotate(m=TruncMonth("created_at")).values("m").annotate(s=Sum("amount")).order_by("m"):
            if item["m"]:
                k = item["m"].strftime("%b %Y")
                if k in months_data:
                    months_data[k] = float(item["s"] or 0)

        return {
            "labels": list(months_data.keys()),
            "data": list(months_data.values()),
        }

    @staticmethod
    def _build_event_types_chart(qs):
        types_count = qs.values("event_type").annotate(c=Count("id")).order_by("-c")
        type_labels_map = dict(EventType.choices)
        labels = []
        data = []
        for t in types_count:
            labels.append(type_labels_map.get(t["event_type"], t["event_type"]))
            data.append(t["c"])
        if not labels:
            labels = ["No Events"]
            data = [0]
        return {"labels": labels, "data": data}

    @staticmethod
    def _build_venue_utilization_chart():
        venues = Venue.objects.annotate(c=Count("events", filter=~Q(events__status=EventStatus.CANCELLED))).order_by("-c")[:7]
        labels = [v.name for v in venues]
        data = [v.c for v in venues]
        return {"labels": labels, "data": data}

    @staticmethod
    def _build_expense_categories_chart():
        cats = Expense.objects.filter(status=ExpenseStatus.APPROVED).values("category").annotate(total=Sum("amount")).order_by("-total")
        cat_map = dict(ExpenseCategory.choices)
        labels = []
        data = []
        for c in cats:
            labels.append(cat_map.get(c["category"], c["category"]))
            data.append(float(c["total"] or 0))
        if not labels:
            labels = ["No Expenses"]
            data = [0]
        return {"labels": labels, "data": data}

    @staticmethod
    def _build_event_spending_chart():
        events = Event.objects.exclude(status=EventStatus.CANCELLED).annotate(
            spent=Coalesce(Sum("expenses__amount", filter=Q(expenses__status=ExpenseStatus.APPROVED)), Decimal(0), output_field=DecimalField())
        ).order_by("-spent")[:6]
        labels = [e.name for e in events]
        budget_data = [float(e.budget) for e in events]
        spent_data = [float(e.spent) for e in events]
        return {"labels": labels, "budget": budget_data, "spent": spent_data}

    # -------------------------------------------------------------
    # LEGACY / BACKWARD-COMPATIBLE HELPERS
    # -------------------------------------------------------------
    @staticmethod
    def full_context():
        now = timezone.now()
        events_stats = Event.objects.aggregate(
            total=Count("id"),
            draft=Count("id", filter=Q(status=EventStatus.DRAFT)),
            submitted=Count("id", filter=Q(status=EventStatus.SUBMITTED)),
            approved=Count("id", filter=Q(status=EventStatus.APPROVED)),
            in_progress=Count("id", filter=Q(status=EventStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=EventStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=EventStatus.CANCELLED)),
        )
        task_stats = EventTask.objects.aggregate(
            total=Count("id"),
            todo=Count("id", filter=Q(status=TaskStatus.TODO)),
            in_progress=Count("id", filter=Q(status=TaskStatus.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            blocked=Count("id", filter=Q(status=TaskStatus.BLOCKED)),
            overdue=Count("id", filter=~Q(status=TaskStatus.COMPLETED) & Q(due_date__lt=now)),
            critical_open=Count("id", filter=Q(priority=TaskPriority.CRITICAL) & ~Q(status=TaskStatus.COMPLETED)),
        )
        approved_exp = Expense.objects.filter(status=ExpenseStatus.APPROVED).aggregate(
            s=Coalesce(Sum("amount"), Decimal(0), output_field=DecimalField())
        )["s"]
        total_budget = Event.objects.exclude(status=EventStatus.CANCELLED).aggregate(
            b=Coalesce(Sum("budget"), Decimal(0), output_field=DecimalField())
        )["b"]
        pending_count = Expense.objects.filter(status=ExpenseStatus.PENDING).count()
        remaining = total_budget - approved_exp
        utilization = (float(approved_exp) / float(total_budget) * 100) if total_budget and float(total_budget) > 0 else 0.0

        return {
            "events": events_stats,
            "tasks": task_stats,
            "finance": {
                "total_budget": total_budget,
                "approved_expenses": approved_exp,
                "remaining_budget": remaining,
                "utilization_pct": round(utilization, 1),
                "pending_approvals": pending_count,
            },
            "upcoming_events": list(Event.objects.filter(start_date__gte=now).exclude(status=EventStatus.CANCELLED).order_by("start_date")[:5]),
            "critical_tasks": list(EventTask.objects.filter(priority=TaskPriority.CRITICAL).exclude(status=TaskStatus.COMPLETED).select_related("event", "assigned_to").order_by("due_date")[:5]),
            "overdue_tasks": list(EventTask.objects.exclude(status=TaskStatus.COMPLETED).filter(due_date__lt=now).select_related("event", "assigned_to").order_by("due_date")[:5]),
            "pending_approvals": list(Event.objects.filter(status=EventStatus.SUBMITTED).select_related("manager", "venue").order_by("updated_at")[:5]),
            "recent_activity": list(AuditLog.objects.select_related("user").order_by("-timestamp")[:8]),
            "staff_assignments": EventStaff.objects.count(),
            "vendor_count": Vendor.objects.filter(is_active=True).count(),
        }

