"""Audit log model — tracks important user actions."""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=40, blank=True)
    entity_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.user} at {self.timestamp:%Y-%m-%d %H:%M}"
