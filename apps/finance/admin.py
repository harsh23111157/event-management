from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "event", "category", "amount", "status", "created_by", "approved_by")
    list_filter = ("status", "category")
    search_fields = ("description", "event__name")
    readonly_fields = ("created_at", "updated_at", "approved_at")
