from django.urls import path

from .views import (EventStaffCreateView, EventTaskCreateView,
                     EventTaskUpdateView, ScheduleCreateView, TaskListView)

urlpatterns = [
    path("tasks/", TaskListView.as_view(), name="task_list"),
    path("events/<int:pk>/tasks/new/", EventTaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/edit/", EventTaskUpdateView.as_view(), name="task_edit"),
    path("events/<int:pk>/staff/new/", EventStaffCreateView.as_view(), name="staff_create"),
    path("events/<int:pk>/schedules/new/", ScheduleCreateView.as_view(), name="schedule_create"),
]
