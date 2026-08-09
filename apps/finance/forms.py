from django import forms

from apps.finance.models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["event", "description", "category", "amount"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-control")
        if user and user.is_event_manager:
            from apps.events.models import Event
            self.fields["event"].queryset = Event.objects.filter(manager=user)


class ExpenseRejectForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}))
