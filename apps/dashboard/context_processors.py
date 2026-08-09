"""Context processors for dashboard and role-aware navigation."""
from django.utils import timezone


def dashboard_nav_context(request):
    ctx = {
        "nav_section": getattr(request, "resolver_match", None) and request.resolver_match.url_name or "",
        "unread_alerts_count": 0,
        "is_admin": False,
        "is_event_manager": False,
        "is_finance": False,
        "is_staff_member": False,
        "can_manage_events": False,
        "can_approve_events": False,
        "can_manage_finance": False,
        "can_manage_users": False,
        "can_view_audit": False,
        "sidebar_pending_events": 0,
        "sidebar_pending_expenses": 0,
        "sidebar_overdue_tasks": 0,
        "sidebar_rejected_events": 0,
        "sidebar_my_overdue": 0,
    }
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        ctx["is_admin"] = user.is_admin
        ctx["is_event_manager"] = user.is_event_manager
        ctx["is_finance"] = user.is_finance
        ctx["is_staff_member"] = user.is_staff_member
        ctx["can_manage_events"] = user.is_admin or user.is_event_manager
        ctx["can_approve_events"] = user.is_admin
        ctx["can_manage_finance"] = user.is_admin or user.is_finance
        ctx["can_manage_users"] = user.is_admin
        ctx["can_view_audit"] = user.is_admin

        try:
            from apps.events.models import Event, EventStatus
            from apps.finance.models import Expense, ExpenseStatus
            from apps.operations.models import EventTask, TaskStatus
            now = timezone.now()

            if user.is_admin:
                p_ev = Event.objects.filter(status=EventStatus.SUBMITTED).count()
                p_ex = Expense.objects.filter(status=ExpenseStatus.PENDING).count()
                od_t = EventTask.objects.exclude(status=TaskStatus.COMPLETED).filter(due_date__lt=now).count()
                ctx["sidebar_pending_events"] = p_ev
                ctx["sidebar_pending_expenses"] = p_ex
                ctx["sidebar_overdue_tasks"] = od_t
                ctx["unread_alerts_count"] = p_ev + p_ex + (1 if od_t > 0 else 0)
            elif user.is_event_manager:
                rej_ev = Event.objects.filter(manager=user, status=EventStatus.REJECTED).count()
                od_t = EventTask.objects.filter(event__manager=user).exclude(status=TaskStatus.COMPLETED).filter(due_date__lt=now).count()
                ctx["sidebar_rejected_events"] = rej_ev
                ctx["sidebar_overdue_tasks"] = od_t
                ctx["unread_alerts_count"] = rej_ev + (1 if od_t > 0 else 0)
            elif user.is_finance:
                p_ex = Expense.objects.filter(status=ExpenseStatus.PENDING).count()
                ctx["sidebar_pending_expenses"] = p_ex
                ctx["unread_alerts_count"] = p_ex
            elif user.is_staff_member:
                my_od = EventTask.objects.filter(assigned_to=user).exclude(status=TaskStatus.COMPLETED).filter(due_date__lt=now).count()
                ctx["sidebar_my_overdue"] = my_od
                ctx["unread_alerts_count"] = my_od
        except Exception:
            pass

    return ctx

