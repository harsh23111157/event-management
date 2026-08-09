import re
from django import forms
from django.core.exceptions import ValidationError

from apps.vendors.models import EventVendor, Vendor, VendorStatus


class VendorForm(forms.ModelForm):
    name = forms.CharField(
        min_length=2,
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Apex Audio & Visuals", "required": "required"}),
        error_messages={"required": "Vendor company name is required.", "min_length": "Vendor name must be at least 2 characters."}
    )
    service_type = forms.CharField(
        min_length=2,
        max_length=120,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Catering, Audio/Visual, Decoration, Security", "required": "required"}),
        error_messages={"required": "Service category is required."}
    )
    contact_person = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. John Doe (Lead Contact)"})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "e.g. contact@vendor.com", "required": "required"}),
        error_messages={"required": "Contact email is required.", "invalid": "Please enter a valid email address."}
    )
    phone = forms.CharField(
        min_length=7,
        max_length=32,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. +91 98765 12345", "required": "required"}),
        error_messages={"required": "Contact phone number is required."}
    )

    class Meta:
        model = Vendor
        fields = ["name", "service_type", "contact_person", "email", "phone", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name or len(name) < 2:
            raise ValidationError("Vendor name must be at least 2 characters.")
        qs = Vendor.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"A vendor named '{name}' already exists.")
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone or not re.match(r"^[\+]?[0-9\s\-\(\)]{7,24}$", phone):
            raise ValidationError("Please enter a valid contact phone number (7–24 digits).")
        return phone


class EventVendorForm(forms.ModelForm):
    contract_amount = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 50000.00", "step": "0.01", "required": "required"}),
        error_messages={"required": "Contract amount is required.", "min_value": "Contract amount must be greater than zero."}
    )

    class Meta:
        model = EventVendor
        fields = ["vendor", "contract_amount", "service_description", "status"]
        widgets = {
            "service_description": forms.Textarea(attrs={"rows": 3, "placeholder": "Deliverables, terms of service, equipment provided..."}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["vendor"].queryset = Vendor.objects.filter(is_active=True).order_by("name")
        self.fields["vendor"].empty_label = "— Select Active Vendor —"
        self.fields["vendor"].required = True

        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        vendor = cleaned.get("vendor")
        if vendor and self.event:
            qs = EventVendor.objects.filter(event=self.event, vendor=vendor)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("vendor", f"Vendor '{vendor.name}' is already contracted for this event.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.event:
            instance.event = self.event
        if commit:
            instance.save()
        return instance

