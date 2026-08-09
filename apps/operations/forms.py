from django import forms

from apps.operations.models import EventStaff, EventTask, Schedule


class EventTaskForm(forms.ModelForm):
    class Meta:
        model = EventTask
        fields = ["title", "description", "assigned_to", "due_date", "priority", "status", "notes"]
        widgets = {
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")
        if event:
            staff_ids = event.staff_assignments.values_list("staff_id", flat=True)
            self.fields["assigned_to"].queryset = self.fields["assigned_to"].queryset.filter(id__in=staff_ids)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.event:
            instance.event = self.event
        if commit:
            instance.save()
        return instance


class EventStaffForm(forms.ModelForm):
    class Meta:
        model = EventStaff
        fields = ["staff", "role"]

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.event:
            instance.event = self.event
        if commit:
            instance.save()
        return instance


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ["title", "description", "start_time", "end_time", "location", "responsible_staff"]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")
        if event:
            self.fields["responsible_staff"].queryset = event.staff_assignments.all()
