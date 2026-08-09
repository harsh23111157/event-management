"""Web views for reports — all server-rendered from real DB queries."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views import View

from .services import ReportService


class EventReportView(LoginRequiredMixin, View):
    template_name = "reports/event_report.html"

    def get(self, request):
        ctx = {
            "report": ReportService.event_status_report(request.user),
            "attendance": ReportService.attendance_report(request.user),
        }
        return render(request, self.template_name, ctx)


class FinanceReportView(LoginRequiredMixin, View):
    template_name = "reports/finance_report.html"

    def get(self, request):
        if not (request.user.is_admin or request.user.is_finance or request.user.is_event_manager):
            raise PermissionDenied("You do not have permission to access financial reports.")
        ctx = {"report": ReportService.finance_report(request.user)}
        return render(request, self.template_name, ctx)


class TaskReportView(LoginRequiredMixin, View):
    template_name = "reports/task_report.html"

    def get(self, request):
        ctx = {"report": ReportService.task_report(request.user)}
        return render(request, self.template_name, ctx)


class VendorReportView(LoginRequiredMixin, View):
    template_name = "reports/vendor_report.html"

    def get(self, request):
        ctx = {"report": ReportService.vendor_report(request.user)}
        return render(request, self.template_name, ctx)
