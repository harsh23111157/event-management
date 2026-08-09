from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, Role
from apps.venues.models import Venue
from apps.events.models import Event, EventStatus, EventType
from apps.vendors.models import Vendor, EventVendor, VendorStatus


class VendorTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="mgr_user", email="mgr@test.com", password="pass", role=Role.EVENT_MANAGER
        )
        self.venue = Venue.objects.create(name="Expo Hall", capacity=500)
        self.now = timezone.now()
        self.event = Event.objects.create(
            name="Vendor Fair", event_type=EventType.OTHER,
            start_date=self.now + timedelta(days=5), end_date=self.now + timedelta(days=6),
            venue=self.venue, manager=self.manager, expected_attendees=100, budget=8000,
            status=EventStatus.APPROVED
        )

    def test_vendor_and_event_vendor(self):
        vendor = Vendor.objects.create(
            name="Top Catering", service_type="Catering", contact_person="Bob", phone="555-4321"
        )
        self.assertEqual(str(vendor), "Top Catering")

        ev = EventVendor.objects.create(
            event=self.event, vendor=vendor, contract_amount=2500, status=VendorStatus.CONFIRMED
        )
        self.assertEqual(ev.status, VendorStatus.CONFIRMED)
        self.assertEqual(ev.contract_amount, 2500)
