from django.contrib.auth.mixins import LoginRequiredMixin
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

