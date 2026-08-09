from django.test import TestCase
from apps.reports.services import ReportService


class ReportsTests(TestCase):
    def test_report_services(self):
        events_report = ReportService.event_status_report()
        self.assertIsNotNone(events_report)
        tasks_report = ReportService.task_report()
        self.assertIsNotNone(tasks_report)
        vendors_report = ReportService.vendor_report()
        self.assertIsNotNone(vendors_report)
        finance_report = ReportService.finance_report()
        self.assertIsNotNone(finance_report)
        attendance_report = ReportService.attendance_report()
        self.assertIsNotNone(attendance_report)
