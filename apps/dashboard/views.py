import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from .services import DashboardService


class DashboardView(LoginRequiredMixin, View):
    template_name = "dashboard/dashboard.html"

    def get(self, request):
        user = request.user
        filters = {
            "status": request.GET.get("status", "").strip(),
            "event_type": request.GET.get("event_type", "").strip(),
            "venue": request.GET.get("venue", "").strip(),
            "date_range": request.GET.get("date_range", "30d").strip(),
        }

        if user.is_admin:
            ctx = DashboardService.get_admin_dashboard(filters)
        elif user.is_event_manager:
            ctx = DashboardService.get_manager_dashboard(user, filters)
        elif user.is_staff_member:
            ctx = DashboardService.get_staff_dashboard(user, filters)
        elif user.is_finance:
            ctx = DashboardService.get_finance_dashboard(filters)
        else:
            ctx = DashboardService.get_admin_dashboard(filters)

        ctx["filters"] = filters
        ctx["current_role"] = user.role
        return render(request, self.template_name, ctx)


class WorkflowGuideView(LoginRequiredMixin, View):
    template_name = "dashboard/workflow_guide.html"

    def get(self, request):
        return render(request, self.template_name, {
            "current_role": request.user.role,
        })


class AiBriefingView(LoginRequiredMixin, View):
    """AJAX endpoint — returns a real-time AI portfolio briefing as JSON."""

    def get(self, request):
        from apps.events.models import Event, EventStatus
        from apps.events.health import generate_portfolio_briefing, compute_event_health

        active_statuses = [
            EventStatus.DRAFT, EventStatus.SUBMITTED,
            EventStatus.APPROVED, EventStatus.IN_PROGRESS,
        ]
        events = (
            Event.objects
            .filter(status__in=active_statuses)
            .prefetch_related(
                "expenses", "tasks", "staff_assignments", "event_vendors"
            )
            .select_related("venue", "manager")
        )

        if request.user.is_event_manager:
            events = events.filter(manager=request.user)

        scored = [compute_event_health(e) for e in events]
        briefing_text = generate_portfolio_briefing(list(events))

        return JsonResponse({
            "briefing": briefing_text,
            "scores": [
                {
                    "id": s.event_id,
                    "name": s.event_name,
                    "score": s.score,
                    "grade": s.grade,
                    "color": s.color,
                    "badge_css": s.badge_css,
                    "summary": s.summary,
                    "icon": s.icon,
                    "factors": s.factors,
                    "recommendations": s.recommendations,
                }
                for s in scored
            ],
        })
