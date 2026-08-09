from django.test import Client, TestCase
from django.urls import reverse
from apps.accounts.models import User, Role
from apps.events.models import Event, EventStatus, EventType
from apps.venues.models import Venue
from apps.dashboard.services import DashboardService
from datetime import timedelta
from django.utils import timezone


class DashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_u", email="admin_u@test.com", password="pass", role=Role.ADMIN, is_staff=True
        )
        self.manager = User.objects.create_user(
            username="mgr_u", email="mgr_u@test.com", password="pass", role=Role.EVENT_MANAGER
        )
        self.finance = User.objects.create_user(
            username="fin_u", email="fin_u@test.com", password="pass", role=Role.FINANCE
        )
        self.staff = User.objects.create_user(
            username="staff_u", email="staff_u@test.com", password="pass", role=Role.STAFF
        )
        self.venue = Venue.objects.create(name="Center Arena", capacity=500)
        self.now = timezone.now()
        self.event = Event.objects.create(
            name="Community Fair",
            event_type=EventType.OTHER,
            start_date=self.now + timedelta(days=5),
            end_date=self.now + timedelta(days=7),
            venue=self.venue,
            manager=self.manager,
            expected_attendees=200,
            budget=10000,
            status=EventStatus.APPROVED,
        )

    def test_dashboard_url_reverse(self):
        url = reverse("dashboard")
        self.assertEqual(url, "/dashboard/")

    def test_dashboard_full_context(self):
        context = DashboardService.full_context()
        self.assertIn("events", context)
        self.assertIn("tasks", context)
        self.assertIn("finance", context)
        self.assertIn("upcoming_events", context)
        self.assertIn("critical_tasks", context)
        self.assertIn("overdue_tasks", context)

    def test_dashboard_view_renders_for_all_roles(self):
        for user in [self.admin, self.manager, self.finance, self.staff]:
            client = Client()
            client.force_login(user)
            resp = client.get("/dashboard/")
            self.assertEqual(resp.status_code, 200, f"Dashboard failed for role {user.role}")
            self.assertContains(resp, "Dashboard")

    def test_dashboard_anonymous_redirect(self):
        client = Client()
        resp = client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.get("Location", ""))
