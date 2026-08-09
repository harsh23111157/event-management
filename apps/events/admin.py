from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "event_type", "start_date", "venue", "manager", "status", "budget")
    list_filter = ("status", "event_type")
    search_fields = ("name", "description")
    date_hierarchy = "start_date"
    readonly_fields = ("created_at", "updated_at", "rejection_reason")
