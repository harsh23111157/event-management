"""Custom user model with role-based access control."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    EVENT_MANAGER = "EVENT_MANAGER", "Event Manager"
    STAFF = "STAFF", "Staff"
    FINANCE = "FINANCE", "Finance"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    phone = models.CharField(max_length=24, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email", "first_name", "last_name"]
    USERNAME_FIELD = "username"

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return f"{self.get_full_name()} ({self.username})"

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_event_manager(self) -> bool:
        return self.role == Role.EVENT_MANAGER

    @property
    def is_finance(self) -> bool:
        return self.role == Role.FINANCE

    @property
    def is_staff_member(self) -> bool:
        return self.role == Role.STAFF
