from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "entity_type", "entity_id", "description")
    list_filter = ("action", "entity_type")
    search_fields = ("description", "user__username")
    readonly_fields = ("user", "action", "entity_type", "entity_id", "description", "timestamp")
    date_hierarchy = "timestamp"
