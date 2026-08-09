import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Role, User


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "autofocus": True, "placeholder": "Enter username"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Enter password"})


class UserForm(forms.ModelForm):
    username = forms.CharField(
        min_length=3,
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. jsmith", "required": "required"}),
        error_messages={"required": "Username is required.", "min_length": "Username must be at least 3 characters."}
    )
    first_name = forms.CharField(
        min_length=1,
        max_length=80,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. John", "required": "required"}),
        error_messages={"required": "First name is required."}
    )
    last_name = forms.CharField(
        min_length=1,
        max_length=80,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Smith", "required": "required"}),
        error_messages={"required": "Last name is required."}
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "e.g. jsmith@eventops.com", "required": "required"}),
        error_messages={"required": "Email address is required.", "invalid": "Please enter a valid email address."}
    )
    role = forms.ChoiceField(
        choices=Role.choices,
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={"required": "System role is required."}
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}),
        required=False,
        help_text="Required for new accounts (minimum 8 characters). Leave blank on existing accounts to keep password unchanged."
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "role", "phone", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        is_new = not (self.instance and self.instance.pk)
        if is_new:
            self.fields["password"].required = True
            self.fields["password"].widget.attrs["required"] = "required"
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-control")

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters.")
        if not re.match(r"^[\w.@+-]+$", username):
            raise ValidationError("Username can only contain letters, numbers, and @/./+/-/_ characters.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Username '{username}' is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("Email address is required.")
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Email '{email}' is already associated with another account.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        is_new = not (self.instance and self.instance.pk)
        if is_new and not password:
            raise ValidationError("Password is required for new accounts.")
        if password and len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

