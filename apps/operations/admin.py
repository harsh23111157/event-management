from django.contrib import admin

from .models import Attendance, EventStaff, EventTask, Schedule


@admin.register(EventStaff)
class EventStaffAdmin(admin.ModelAdmin):
    list_display = ("event", "staff", "role", "assigned_at")
    list_filter = ("role",)
    search_fields = ("event__name", "staff__username")


@admin.register(EventTask)
class EventTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "assigned_to", "priority", "status", "due_date", "completed_at")
    list_filter = ("status", "priority")
    search_fields = ("title", "event__name")
    readonly_fields = ("created_at", "updated_at", "completed_at")


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "start_time", "end_time", "location", "responsible_staff")
    search_fields = ("title", "event__name")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("event", "staff", "status", "check_in", "check_out")
    list_filter = ("status",)
    search_fields = ("event__name", "staff__username")
