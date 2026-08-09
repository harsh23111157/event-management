from django.contrib import admin

from .models import Venue


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "contact_person", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "address", "contact_person")
