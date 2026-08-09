from datetime import timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, Role
from apps.venues.models import Venue
from apps.events.models import Event, EventStatus, EventType
from apps.events.services import EventWorkflowService
from apps.operations.models import EventStaff, EventTask, TaskPriority, TaskStatus


class EventWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_user", email="admin@test.com", password="pass",
            role=Role.ADMIN, is_staff=True
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
        # Create task and staff assignment required by workflow transitions
        self.task = EventTask.objects.create(
            event=self.event,
            title="Initial setup",
            due_date=self.now + timedelta(days=5),
            priority=TaskPriority.HIGH,
            status=TaskStatus.TODO,
        )
        EventStaff.objects.create(event=self.event, staff=self.admin, role="Coordinator")

    def test_workflow_lifecycle(self):
        # 1. Submit event (Manager)
        event = EventWorkflowService.submit_event(self.event, self.manager)
        self.assertEqual(event.status, EventStatus.SUBMITTED)

        # 2. Approve event (Admin)
        event = EventWorkflowService.approve_event(event, self.admin)
        self.assertEqual(event.status, EventStatus.APPROVED)

        # 3. Start event (Manager)
        event = EventWorkflowService.start_event(event, self.manager)
        self.assertEqual(event.status, EventStatus.IN_PROGRESS)

        # 4. Complete task and Complete event (Manager)
        self.task.status = TaskStatus.COMPLETED
        self.task.save()
        event = EventWorkflowService.complete_event(event, self.manager)
        self.assertEqual(event.status, EventStatus.COMPLETED)

    def test_event_validation_dates(self):
        bad_event = Event(
            name="Bad Dates",
            event_type=EventType.MEETUP,
            start_date=self.now + timedelta(days=5),
            end_date=self.now + timedelta(days=2),
            venue=self.venue,
            manager=self.manager,
            expected_attendees=50,
            budget=500,
        )
        with self.assertRaises(ValidationError):
            bad_event.clean()

    def test_deterministic_readiness_calculation(self):
        from apps.events.services import EventReadinessService
        readiness = EventReadinessService.calculate_readiness(self.event)
        self.assertIn("score", readiness)
        self.assertIn("status", readiness)
        self.assertIn("checklist", readiness)
        self.assertGreaterEqual(readiness["score"], 0)
        self.assertLessEqual(readiness["score"], 100)

    def test_rbac_event_creation_permissions(self):
        from django.test import Client
        staff_user = User.objects.create_user(username="staff_u2", password="pass", role=Role.STAFF)
        client = Client()
        client.force_login(staff_user)
        # Staff cannot create events (HTTP 403)
        resp = client.get("/events/new/")
        self.assertEqual(resp.status_code, 403)

    def test_manager_cannot_edit_other_manager_event(self):
        from django.test import Client
        other_manager = User.objects.create_user(username="other_mgr", password="pass", role=Role.EVENT_MANAGER)
        client = Client()
        client.force_login(other_manager)
        # Attempt to edit self.event managed by self.manager -> 403
        resp = client.get(f"/events/{self.event.id}/edit/")
        self.assertEqual(resp.status_code, 403)

    def test_edit_lock_on_submitted_event(self):
        from django.test import Client
        self.event.status = EventStatus.SUBMITTED
        self.event.save()
        client = Client()
        client.force_login(self.manager)
        # Cannot edit submitted event -> 403
        resp = client.get(f"/events/{self.event.id}/edit/")
        self.assertEqual(resp.status_code, 403)

