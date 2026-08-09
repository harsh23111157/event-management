from django import forms

from apps.events.models import Event, EventType, EventStatus


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "description", "event_type", "start_date", "end_date",
                  "venue", "manager", "expected_attendees", "budget"]
        widgets = {
            "start_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "end_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end <= start:
            self.add_error("end_date", "End date must be after start date.")
        budget = cleaned.get("budget")
        if budget is not None and budget <= 0:
            self.add_error("budget", "Budget must be greater than zero.")
        attendees = cleaned.get("expected_attendees")
        venue = cleaned.get("venue")
        if attendees and venue and attendees > venue.capacity:
            self.add_error("expected_attendees", "Expected attendees exceed venue capacity.")
        return cleaned
