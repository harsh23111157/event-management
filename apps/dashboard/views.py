from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .services import DashboardService


class DashboardView(LoginRequiredMixin, View):
    template_name = "dashboard/dashboard.html"

    def get(self, request):
        ctx = DashboardService.full_context()
        ctx["user_role"] = request.user.role
        return render(request, self.template_name, ctx)
