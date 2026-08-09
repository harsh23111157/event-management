from django import forms
from django.core.exceptions import ValidationError

from apps.events.models import Event
from apps.finance.models import Expense, ExpenseCategory


class ExpenseForm(forms.ModelForm):
    description = forms.CharField(
        min_length=3,
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Stage lighting rental deposit", "required": "required"}),
        error_messages={"required": "Expense description is required.", "min_length": "Description must be at least 3 characters."}
    )
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 12500.00", "step": "0.01", "min": "0.01", "required": "required"}),
        error_messages={"required": "Expense amount is required.", "min_value": "Expense amount must be greater than zero."}
    )

    class Meta:
        model = Expense
        fields = ["event", "description", "category", "amount"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        event_qs = Event.objects.exclude(status="CANCELLED").order_by("name")
        if user and user.is_event_manager:
            event_qs = event_qs.filter(manager=user)
        self.fields["event"].queryset = event_qs
        self.fields["event"].empty_label = "— Select Target Event —"
        self.fields["event"].required = True

        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")

    def clean_description(self):
        desc = self.cleaned_data.get("description", "").strip()
        if not desc or len(desc) < 3:
            raise ValidationError("Expense description must be at least 3 characters.")
        return desc


class ExpenseRejectForm(forms.Form):
    reason = forms.CharField(
        min_length=5,
        required=True,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Specify the justification for rejection...", "required": "required"}),
        error_messages={"required": "A rejection reason is required.", "min_length": "Reason must be at least 5 characters."}
    )

    def clean_reason(self):
        reason = self.cleaned_data.get("reason", "").strip()
        if not reason or len(reason) < 5:
            raise ValidationError("Rejection reason must be at least 5 characters.")
        return reason

