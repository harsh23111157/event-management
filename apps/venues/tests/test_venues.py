from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.venues.models import Venue


class VenueModelTests(TestCase):
    def test_create_venue(self):
        venue = Venue.objects.create(
            name="Main Auditorium",
            address="100 University Ave",
            capacity=500,
            contact_person="Alice",
            contact_phone="1234567890",
        )
        self.assertEqual(str(venue), "Main Auditorium")
        self.assertTrue(venue.is_active)
        self.assertEqual(venue.capacity, 500)
