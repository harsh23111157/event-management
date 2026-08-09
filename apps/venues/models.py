"""Venue model."""
from django.db import models


class Venue(models.Model):
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=0)
    contact_person = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(capacity__gte=0), name="venue_capacity_nonneg"),
        ]

    def __str__(self) -> str:
        return self.name
