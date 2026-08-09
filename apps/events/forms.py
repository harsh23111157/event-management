from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.accounts.models import Role
from apps.events.models import Event, EventStatus, EventType
from apps.venues.models import Venue

User = get_user_model()


class EventForm(forms.ModelForm):
    name = forms.CharField(
        min_length=3,
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Annual Tech Leadership Summit 2026", "required": "required"}),
        error_messages={"required": "Event name is required.", "min_length": "Event name must be at least 3 characters."}
    )
    expected_attendees = forms.IntegerField(
        min_value=1,
        max_value=1000000,
        required=True,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 250", "min": "1", "required": "required"}),
        error_messages={"required": "Expected attendees count is required.", "min_value": "Expected attendees must be at least 1."}
    )
    budget = forms.DecimalField(
        min_value=1.00,
        max_digits=12,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 150000.00", "step": "0.01", "min": "1", "required": "required"}),
        error_messages={"required": "Budget allocation is required.", "min_value": "Budget must be greater than zero."}
    )
    start_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "required": "required"}, format="%Y-%m-%dT%H:%M"),
        error_messages={"required": "Start date and time is required."}
    )
    end_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "required": "required"}, format="%Y-%m-%dT%H:%M"),
        error_messages={"required": "End date and time is required."}
    )

    class Meta:
        model = Event
        fields = ["name", "description", "event_type", "start_date", "end_date",
                  "venue", "manager", "expected_attendees", "budget"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Event brief, goals, target audience, schedule highlights..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["venue"].queryset = Venue.objects.filter(is_active=True).order_by("name")
        self.fields["venue"].empty_label = "— Select Venue Location —"
        self.fields["venue"].required = True

        self.fields["manager"].queryset = User.objects.filter(is_active=True).filter(
            Q(role=Role.EVENT_MANAGER) | Q(role=Role.ADMIN)
        ).order_by("first_name", "last_name")
        self.fields["manager"].empty_label = "— Select Assigned Event Manager —"
        self.fields["manager"].required = True

        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name or len(name) < 3:
            raise ValidationError("Event name must be at least 3 characters.")
        return name

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end <= start:
            self.add_error("end_date", "End date/time must be strictly after the start date/time.")
        
        budget = cleaned.get("budget")
        if budget is not None and budget <= 0:
            self.add_error("budget", "Budget must be greater than zero.")
        
        attendees = cleaned.get("expected_attendees")
        venue = cleaned.get("venue")
        if attendees and venue and attendees > venue.capacity:
            self.add_error(
                "expected_attendees",
                f"Expected attendees ({attendees}) exceeds maximum capacity of {venue.name} ({venue.capacity} pax)."
            )
        return cleaned

