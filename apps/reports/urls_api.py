"""REST API for reports."""
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import ReportService


class EventReportAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(ReportService.event_status_report())


class FinanceReportAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(ReportService.finance_report())


class TaskReportAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(ReportService.task_report())


class VendorReportAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(ReportService.vendor_report())


urlpatterns = [
    path("reports/events/", EventReportAPIView.as_view(), name="api_report_events"),
    path("reports/finance/", FinanceReportAPIView.as_view(), name="api_report_finance"),
    path("reports/tasks/", TaskReportAPIView.as_view(), name="api_report_tasks"),
    path("reports/vendors/", VendorReportAPIView.as_view(), name="api_report_vendors"),
]
