from django.urls import path

from .views import (EventReportView, FinanceReportView, TaskReportView,
                     VendorReportView)

urlpatterns = [
    path("events/", EventReportView.as_view(), name="report_events"),
    path("finance/", FinanceReportView.as_view(), name="report_finance"),
    path("tasks/", TaskReportView.as_view(), name="report_tasks"),
    path("vendors/", VendorReportView.as_view(), name="report_vendors"),
]
