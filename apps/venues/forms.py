import re
from django import forms
from django.core.exceptions import ValidationError

from apps.venues.models import Venue


class VenueForm(forms.ModelForm):
    name = forms.CharField(
        min_length=2,
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Grand Horizon Convention Center", "required": "required"}),
        error_messages={"required": "Venue name is required.", "min_length": "Venue name must be at least 2 characters."}
    )
    capacity = forms.IntegerField(
        min_value=1,
        max_value=1000000,
        required=True,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 500", "required": "required", "min": "1"}),
        error_messages={"required": "Maximum guest capacity is required.", "min_value": "Capacity must be at least 1 pax."}
    )
    address = forms.CharField(
        min_length=5,
        required=True,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Full street address, city, state, postal code...", "required": "required"}),
        error_messages={"required": "Physical address is required.", "min_length": "Address must be at least 5 characters long."}
    )
    contact_person = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Jane Doe (Venue Manager)"})
    )
    contact_phone = forms.CharField(
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. +91 98765 43210"})
    )
    contact_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "e.g. venue@example.com"}),
        error_messages={"invalid": "Please enter a valid email address."}
    )

    class Meta:
        model = Venue
        fields = ["name", "address", "capacity", "contact_person", "contact_phone", "contact_email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name or len(name) < 2:
            raise ValidationError("Venue name must be at least 2 characters.")
        qs = Venue.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"A venue named '{name}' already exists.")
        return name

    def clean_address(self):
        address = self.cleaned_data.get("address", "").strip()
        if not address or len(address) < 5:
            raise ValidationError("Physical address must be at least 5 characters long.")
        return address

    def clean_contact_phone(self):
        phone = self.cleaned_data.get("contact_phone", "").strip()
        if phone:
            # Allow digits, spaces, dashes, parentheses, leading plus
            if not re.match(r"^[\+]?[0-9\s\-\(\)]{7,24}$", phone):
                raise ValidationError("Please enter a valid phone number (7–24 digits).")
        return phone

