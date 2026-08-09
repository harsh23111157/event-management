from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, Role
from apps.venues.models import Venue
from apps.events.models import Event, EventStatus, EventType
from apps.finance.models import Expense, ExpenseCategory, ExpenseStatus, ExpenseService


class FinanceWorkflowTests(TestCase):
    def setUp(self):
        self.finance = User.objects.create_user(
            username="fin_user", email="fin@test.com", password="pass",
            role=Role.FINANCE
        )
        self.manager = User.objects.create_user(
            username="mgr_user", email="mgr@test.com", password="pass",
            role=Role.EVENT_MANAGER
        )
        self.venue = Venue.objects.create(name="Expo Hall", capacity=1000)
        self.now = timezone.now()
        self.event = Event.objects.create(
            name="Tech Summit",
            event_type=EventType.CONFERENCE,
            start_date=self.now + timedelta(days=10),
            end_date=self.now + timedelta(days=12),
            venue=self.venue,
            manager=self.manager,
            expected_attendees=300,
            budget=15000,
            status=EventStatus.DRAFT,
        )

    def test_expense_approval_flow(self):
        expense = Expense.objects.create(
            event=self.event,
            description="Stage lighting",
            category=ExpenseCategory.EQUIPMENT,
            amount=1200,
            created_by=self.manager,
            status=ExpenseStatus.PENDING,
        )
        # Approve
        approved = ExpenseService.approve(expense, self.finance)
        self.assertEqual(approved.status, ExpenseStatus.APPROVED)
        self.assertEqual(approved.approved_by, self.finance)
        self.assertIsNotNone(approved.approved_at)

    def test_expense_rejection_flow(self):
        expense = Expense.objects.create(
            event=self.event,
            description="Unnecessary snacks",
            category=ExpenseCategory.CATERING,
            amount=300,
            created_by=self.manager,
            status=ExpenseStatus.PENDING,
        )
        # Reject with reason
        rejected = ExpenseService.reject(expense, self.finance, reason="Budget exceeded")
        self.assertEqual(rejected.status, ExpenseStatus.REJECTED)
        self.assertEqual(rejected.rejection_reason, "Budget exceeded")

    def test_staff_cannot_approve_expense(self):
        from django.test import Client
        staff = User.objects.create_user(username="staff_fin", password="pass", role=Role.STAFF)
        expense = Expense.objects.create(
            event=self.event, description="Cables", category=ExpenseCategory.EQUIPMENT,
            amount=200, created_by=self.manager, status=ExpenseStatus.PENDING
        )
        client = Client()
        client.force_login(staff)
        # Attempt to approve expense -> HTTP 403
        resp = client.post(f"/expenses/{expense.id}/approve/")
        self.assertEqual(resp.status_code, 403)

