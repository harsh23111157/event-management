"""Seed demo data for development and testing."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed demo users, venues, events, tasks, vendors, and expenses."

    def handle(self, *args, **options):
        from apps.accounts.models import User, Role
        from apps.venues.models import Venue
        from apps.events.models import Event, EventType, EventStatus
        from apps.operations.models import EventTask, TaskStatus, TaskPriority, EventStaff
        from apps.vendors.models import Vendor, EventVendor, VendorStatus
        from apps.finance.models import Expense, ExpenseCategory, ExpenseStatus

        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"role": Role.ADMIN, "email": "admin@eventops.local",
                      "first_name": "Admin", "last_name": "User", "is_staff": True, "is_superuser": True},
        )
        admin.set_password("admin12345")
        admin.save()

        manager, _ = User.objects.get_or_create(
            username="manager",
            defaults={"role": Role.EVENT_MANAGER, "email": "manager@eventops.local",
                      "first_name": "Event", "last_name": "Manager"},
        )
        manager.set_password("manager12345")
        manager.save()

        finance, _ = User.objects.get_or_create(
            username="finance",
            defaults={"role": Role.FINANCE, "email": "finance@eventops.local",
                      "first_name": "Finance", "last_name": "Officer"},
        )
        finance.set_password("finance12345")
        finance.save()

        staff, _ = User.objects.get_or_create(
            username="staff",
            defaults={"role": Role.STAFF, "email": "staff@eventops.local",
                      "first_name": "Staff", "last_name": "Member"},
        )
        staff.set_password("staff12345")
        staff.save()

        venue1, _ = Venue.objects.get_or_create(name="Grand Conference Hall", defaults={"capacity": 500, "address": "123 Main St", "contact_person": "Jane Doe", "contact_phone": "555-0100"})
        venue2, _ = Venue.objects.get_or_create(name="Tech Hub Auditorium", defaults={"capacity": 300, "address": "456 Tech Blvd", "contact_person": "John Smith", "contact_phone": "555-0200"})
        venue3, _ = Venue.objects.get_or_create(name="Sports Complex", defaults={"capacity": 1000, "address": "789 Stadium Rd", "contact_person": "Coach Brown", "contact_phone": "555-0300"})

        now = timezone.now()

        event1, _ = Event.objects.get_or_create(name="Annual Tech Conference 2026", defaults={
            "event_type": EventType.CONFERENCE, "start_date": now + timedelta(days=30),
            "end_date": now + timedelta(days=32), "venue": venue1, "manager": manager,
            "expected_attendees": 400, "budget": 50000, "status": EventStatus.DRAFT,
        })

        event2, _ = Event.objects.get_or_create(name="Spring Hackathon", defaults={
            "event_type": EventType.HACKATHON, "start_date": now + timedelta(days=14),
            "end_date": now + timedelta(days=16), "venue": venue2, "manager": manager,
            "expected_attendees": 200, "budget": 25000, "status": EventStatus.SUBMITTED,
        })

        event3, _ = Event.objects.get_or_create(name="Team Workshop: Django Deep Dive", defaults={
            "event_type": EventType.WORKSHOP, "start_date": now - timedelta(days=7),
            "end_date": now - timedelta(days=6), "venue": venue2, "manager": manager,
            "expected_attendees": 50, "budget": 5000, "status": EventStatus.COMPLETED,
        })

        EventStaff.objects.get_or_create(event=event1, staff=staff, defaults={"role": "Logistics"})
        EventStaff.objects.get_or_create(event=event2, staff=staff, defaults={"role": "Setup"})

        EventTask.objects.get_or_create(event=event1, title="Book catering", defaults={"assigned_to": staff, "due_date": now + timedelta(days=10), "priority": TaskPriority.HIGH, "status": TaskStatus.TODO})
        EventTask.objects.get_or_create(event=event1, title="Send invitations", defaults={"assigned_to": staff, "due_date": now + timedelta(days=7), "priority": TaskPriority.CRITICAL, "status": TaskStatus.IN_PROGRESS})
        EventTask.objects.get_or_create(event=event2, title="Arrange WiFi", defaults={"assigned_to": staff, "due_date": now + timedelta(days=5), "priority": TaskPriority.CRITICAL, "status": TaskStatus.COMPLETED})
        EventTask.objects.get_or_create(event=event3, title="Prepare materials", defaults={"assigned_to": staff, "due_date": now - timedelta(days=10), "priority": TaskPriority.MEDIUM, "status": TaskStatus.COMPLETED})

        vendor1, _ = Vendor.objects.get_or_create(name="Catering Plus", defaults={"service_type": "Catering", "contact_person": "Chef Mike", "phone": "555-1000"})
        vendor2, _ = Vendor.objects.get_or_create(name="AV Solutions", defaults={"service_type": "Audio/Visual", "contact_person": "Sound Sally", "phone": "555-2000"})

        EventVendor.objects.get_or_create(event=event1, vendor=vendor1, defaults={"contract_amount": 8000, "status": VendorStatus.PLANNED})
        EventVendor.objects.get_or_create(event=event1, vendor=vendor2, defaults={"contract_amount": 5000, "status": VendorStatus.CONFIRMED})

        Expense.objects.get_or_create(event=event1, description="Catering deposit", defaults={"category": ExpenseCategory.CATERING, "amount": 3000, "created_by": manager, "status": ExpenseStatus.PENDING})
        Expense.objects.get_or_create(event=event2, description="AV equipment rental", defaults={"category": ExpenseCategory.EQUIPMENT, "amount": 2000, "created_by": manager, "status": ExpenseStatus.APPROVED, "approved_by": finance})
        Expense.objects.get_or_create(event=event3, description="Printing materials", defaults={"category": ExpenseCategory.PRINTING, "amount": 500, "created_by": manager, "status": ExpenseStatus.APPROVED, "approved_by": finance})

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Login credentials:")
        self.stdout.write("  admin / admin12345 (Admin)")
        self.stdout.write("  manager / manager12345 (Event Manager)")
        self.stdout.write("  finance / finance12345 (Finance)")
        self.stdout.write("  staff / staff12345 (Staff)")
