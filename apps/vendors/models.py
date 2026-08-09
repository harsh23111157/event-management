"""Vendor and EventVendor models."""
from django.db import models

from apps.events.models import Event


class Vendor(models.Model):
    name = models.CharField(max_length=200, unique=True)
    service_type = models.CharField(max_length=120, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class VendorStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    CONFIRMED = "CONFIRMED", "Confirmed"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class EventVendor(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="vendor_assignments")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="event_assignments")
    contract_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=VendorStatus.choices, default=VendorStatus.PLANNED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "vendor")
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(contract_amount__gte=0), name="vendor_amount_nonneg"),
        ]

    def __str__(self) -> str:
        return f"{self.vendor} @ {self.event}"
