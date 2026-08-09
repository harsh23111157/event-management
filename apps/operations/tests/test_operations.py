from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, Role
from apps.venues.models import Venue
from apps.events.models import Event, EventStatus, EventType
from apps.operations.models import EventTask, TaskStatus, TaskPriority, EventStaff, Schedule, Attendance, AttendanceStatus


class OperationsTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="mgr_user", email="mgr@test.com", password="pass", role=Role.EVENT_MANAGER
        )
        self.staff = User.objects.create_user(
            username="staff_user", email="staff@test.com", password="pass", role=Role.STAFF
        )
        self.venue = Venue.objects.create(name="Expo Hall", capacity=500)
        self.now = timezone.now()
        self.event = Event.objects.create(
            name="Operations Summit", event_type=EventType.WORKSHOP,
            start_date=self.now + timedelta(days=2), end_date=self.now + timedelta(days=4),
            venue=self.venue, manager=self.manager, expected_attendees=100, budget=5000,
            status=EventStatus.APPROVED
        )

    def test_task_creation(self):
        task = EventTask.objects.create(
            event=self.event, title="Check audio", assigned_to=self.staff,
            due_date=self.now + timedelta(days=1), priority=TaskPriority.HIGH,
            status=TaskStatus.TODO
        )
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(str(task), f"Check audio ({self.event})")

    def test_staff_assignment_and_attendance(self):
        staff_assignment = EventStaff.objects.create(event=self.event, staff=self.staff, role="Lead Tech")
        self.assertEqual(str(staff_assignment), f"{self.staff} @ {self.event}")

        attendance = Attendance.objects.create(
            event=self.event, staff=self.staff, status=AttendanceStatus.PRESENT
        )
        self.assertEqual(attendance.status, AttendanceStatus.PRESENT)

    def test_staff_cannot_edit_other_staff_task(self):
        from django.test import Client
        other_staff = User.objects.create_user(username="other_staff", password="pass", role=Role.STAFF)
        task = EventTask.objects.create(
            event=self.event, title="Stage Wiring", assigned_to=self.staff,
            due_date=self.now + timedelta(days=1), priority=TaskPriority.HIGH,
            status=TaskStatus.TODO
        )
        client = Client()
        client.force_login(other_staff)
        # Attempt to edit task assigned to another staff member -> HTTP 403
        resp = client.get(f"/operations/tasks/{task.id}/edit/")
        self.assertEqual(resp.status_code, 403)

    def test_staff_attendance_checkin_checkout(self):
        from django.test import Client
        EventStaff.objects.create(event=self.event, staff=self.staff, role="Lead Tech")
        client = Client()
        client.force_login(self.staff)
        # Check in
        resp = client.post(f"/operations/events/{self.event.id}/checkin/")
        self.assertEqual(resp.status_code, 302)
        att = Attendance.objects.get(event=self.event, staff=self.staff)
        self.assertIsNotNone(att.check_in)

        # Check out
        resp = client.post(f"/operations/events/{self.event.id}/checkout/")
        self.assertEqual(resp.status_code, 302)
        att.refresh_from_db()
        self.assertIsNotNone(att.check_out)

    def test_task_form_staff_selection_and_notification(self):
        from apps.operations.forms import EventTaskForm
        from apps.operations.models import Notification, NotificationType
        form_data = {
            "title": "Set up audio microphones",
            "due_date": (self.now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "priority": TaskPriority.HIGH,
            "status": TaskStatus.TODO,
            "assigned_to": self.staff.id,
            "description": "Ensure 4 wireless mics are calibrated.",
            "notes": "",
        }
        form = EventTaskForm(data=form_data, event=self.event, user=self.manager)
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save()
        self.assertEqual(task.assigned_to, self.staff)
        # Check that EventStaff was auto-created
        self.assertTrue(EventStaff.objects.filter(event=self.event, staff=self.staff).exists())
        # Check that Notification was sent to staff
        notif = Notification.objects.filter(recipient=self.staff, notification_type=NotificationType.TASK_ASSIGNED).first()
        self.assertIsNotNone(notif)
        self.assertIn("Set up audio microphones", notif.title)

    def test_staff_task_update_notifies_manager(self):
        from django.test import Client
        from apps.operations.models import Notification, NotificationType
        task = EventTask.objects.create(
            event=self.event, title="Stage Lighting", assigned_to=self.staff,
            due_date=self.now + timedelta(days=1), priority=TaskPriority.MEDIUM,
            status=TaskStatus.TODO
        )
        client = Client()
        client.force_login(self.staff)
        resp = client.post(f"/operations/tasks/{task.id}/edit/", {
            "status": TaskStatus.IN_PROGRESS,
            "notes": "Lamps tested and working.",
        })
        self.assertEqual(resp.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)
        # Manager should have received a notification
        notif = Notification.objects.filter(recipient=self.manager, notification_type=NotificationType.TASK_UPDATED).first()
        self.assertIsNotNone(notif)

    def test_manager_attendance_record_and_quick_action(self):
        from django.test import Client
        EventStaff.objects.create(event=self.event, staff=self.staff, role="Lead Tech")
        client = Client()
        client.force_login(self.manager)

        # Quick action: checkin
        resp = client.post(f"/operations/events/{self.event.id}/attendance/checkin/", {
            "staff_id": self.staff.id
        })
        self.assertEqual(resp.status_code, 302)
        att = Attendance.objects.get(event=self.event, staff=self.staff)
        self.assertEqual(att.status, AttendanceStatus.PRESENT)
        self.assertIsNotNone(att.check_in)

        # Quick action: late
        resp = client.post(f"/operations/events/{self.event.id}/attendance/late/", {
            "staff_id": self.staff.id
        })
        self.assertEqual(resp.status_code, 302)
        att.refresh_from_db()
        self.assertEqual(att.status, AttendanceStatus.LATE)

        # Record view update
        resp = client.post(f"/operations/events/{self.event.id}/attendance/record/", {
            "staff": self.staff.id,
            "status": AttendanceStatus.PRESENT,
        })
        self.assertEqual(resp.status_code, 302)
        att.refresh_from_db()
        self.assertEqual(att.status, AttendanceStatus.PRESENT)

    def test_staff_attendance_checkout_without_prior_checkin_does_not_404(self):
        from django.test import Client
        EventStaff.objects.create(event=self.event, staff=self.staff, role="Lead Tech")
        client = Client()
        client.force_login(self.staff)

        # Post directly to checkout without checking in first -> should succeed 302, not 404
        resp = client.post(f"/operations/events/{self.event.id}/checkout/")
        self.assertEqual(resp.status_code, 302)
        att = Attendance.objects.get(event=self.event, staff=self.staff)
        self.assertIsNotNone(att.check_out)



