from django.urls import path

from .views import (
    AttendanceCheckInView, AttendanceCheckOutView, AttendanceListView,
    EventStaffCreateView, EventTaskCreateView, EventTaskUpdateView,
    GlobalEventTaskCreateView, ManagerAttendanceQuickActionView,
    ManagerAttendanceRecordView, NotificationListView,
    NotificationMarkAllReadView, NotificationMarkReadView,
    ScheduleCreateView, TaskListView
)

urlpatterns = [
    path("tasks/", TaskListView.as_view(), name="task_list"),
    path("tasks/new/", GlobalEventTaskCreateView.as_view(), name="task_create_global"),
    path("events/<int:pk>/tasks/new/", EventTaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/edit/", EventTaskUpdateView.as_view(), name="task_edit"),
    path("events/<int:pk>/staff/new/", EventStaffCreateView.as_view(), name="staff_create"),
    path("events/<int:pk>/schedules/new/", ScheduleCreateView.as_view(), name="schedule_create"),
    path("attendance/", AttendanceListView.as_view(), name="attendance_list"),
    path("events/<int:pk>/checkin/", AttendanceCheckInView.as_view(), name="attendance_checkin"),
    path("events/<int:pk>/checkout/", AttendanceCheckOutView.as_view(), name="attendance_checkout"),
    path("events/<int:pk>/attendance/record/", ManagerAttendanceRecordView.as_view(), name="attendance_record"),
    path("events/<int:pk>/attendance/<str:action>/", ManagerAttendanceQuickActionView.as_view(), name="attendance_quick_action"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/mark-all-read/", NotificationMarkAllReadView.as_view(), name="notifications_mark_all_read"),
    path("notifications/<int:pk>/mark-read/", NotificationMarkReadView.as_view(), name="notification_mark_read"),
]

