from django.contrib import admin

from .models import EventVendor, Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "service_type", "contact_person", "phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "service_type", "contact_person")


@admin.register(EventVendor)
class EventVendorAdmin(admin.ModelAdmin):
    list_display = ("vendor", "event", "contract_amount", "status")
    list_filter = ("status",)
    search_fields = ("vendor__name", "event__name")
    readonly_fields = ("created_at",)
