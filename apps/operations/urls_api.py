from django.urls import path
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.events.models import Event
from apps.operations.models import EventTask, TaskStatus

from .serializers import EventStaffSerializer, EventTaskSerializer, ScheduleSerializer
from apps.operations.models import EventStaff, Schedule


class TaskListCreateView(ListCreateAPIView):
    serializer_class = EventTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = EventTask.objects.select_related("event", "assigned_to")
        if self.request.user.is_staff_member:
            qs = qs.filter(assigned_to=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only event managers or admins can create tasks.")
        return super().create(request, *args, **kwargs)


class TaskDetailView(RetrieveUpdateAPIView):
    serializer_class = EventTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = EventTask.objects.select_related("event", "assigned_to")
        if self.request.user.is_staff_member:
            qs = qs.filter(assigned_to=self.request.user)
        return qs

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        if request.user.is_staff_member and task.assigned_to_id != request.user.id:
            raise PermissionDenied("Staff can only update their own assigned tasks.")
        if not (request.user.is_staff_member or is_event_manager_or_admin(request.user)):
            raise PermissionDenied("Not authorized.")
        return super().update(request, *args, **kwargs)


class StaffListCreateView(ListCreateAPIView):
    serializer_class = EventStaffSerializer
    permission_classes = [IsAuthenticated]
    queryset = EventStaff.objects.select_related("event", "staff")

    def create(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only event managers or admins can assign staff.")
        return super().create(request, *args, **kwargs)


class ScheduleListCreateView(ListCreateAPIView):
    serializer_class = ScheduleSerializer
    permission_classes = [IsAuthenticated]
    queryset = Schedule.objects.select_related("event", "responsible_staff")

    def create(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only event managers or admins can create schedules.")
        return super().create(request, *args, **kwargs)


urlpatterns = [
    path("tasks/", TaskListCreateView.as_view(), name="api_task_list"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="api_task_detail"),
    path("staff/", StaffListCreateView.as_view(), name="api_staff_list"),
    path("schedules/", ScheduleListCreateView.as_view(), name="api_schedule_list"),
]
