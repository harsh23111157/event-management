"""Web views for reports — all server-rendered, all from real DB data."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .services import ReportService


class EventReportView(LoginRequiredMixin, View):
    template_name = "reports/event_report.html"

    def get(self, request):
        ctx = {"report": ReportService.event_status_report()}
        return render(request, self.template_name, ctx)


class FinanceReportView(LoginRequiredMixin, View):
    template_name = "reports/finance_report.html"

    def get(self, request):
        ctx = {"report": ReportService.finance_report()}
        return render(request, self.template_name, ctx)


class TaskReportView(LoginRequiredMixin, View):
    template_name = "reports/task_report.html"

    def get(self, request):
        ctx = {"report": ReportService.task_report()}
        return render(request, self.template_name, ctx)


class VendorReportView(LoginRequiredMixin, View):
    template_name = "reports/vendor_report.html"

    def get(self, request):
        ctx = {"report": ReportService.vendor_report()}
        return render(request, self.template_name, ctx)
