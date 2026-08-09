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


class VenueFormTests(TestCase):
    def test_venue_form_requires_mandatory_fields(self):
        from apps.venues.forms import VenueForm
        # Blank form must fail validation
        form = VenueForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("capacity", form.errors)
        self.assertIn("address", form.errors)

    def test_venue_form_rejects_zero_or_negative_capacity(self):
        from apps.venues.forms import VenueForm
        form = VenueForm(data={"name": "Hall C", "capacity": 0, "address": "123 Main Street"})
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)

    def test_venue_form_valid_submission(self):
        from apps.venues.forms import VenueForm
        form = VenueForm(data={"name": "Hall C", "capacity": 150, "address": "123 Main Street, City", "is_active": True})
        self.assertTrue(form.is_valid(), form.errors)
        v = form.save()
        self.assertEqual(v.capacity, 150)

