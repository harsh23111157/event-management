"""REST API views for events and workflow actions."""
from django.urls import path
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import (CreateAPIView, DestroyAPIView,
                                      ListAPIView, RetrieveAPIView, UpdateAPIView)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (IsAdmin, IsEventManagerOrAdmin,
                                        is_event_manager_or_admin)
from apps.events.models import Event
from apps.events.services import EventWorkflowService

from .serializers import EventSerializer


class EventListCreateView(ListAPIView, CreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Event.objects.select_related("venue", "manager")
        if self.request.user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=self.request.user).distinct()
        return qs

    def create(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only event managers or admins can create events.")
        return super().create(request, *args, **kwargs)


class EventDetailView(RetrieveAPIView, UpdateAPIView, DestroyAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Event.objects.select_related("venue", "manager")
        if self.request.user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=self.request.user).distinct()
        return qs

    def update(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only event managers or admins can edit events.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("Only admins can delete events.")
        return super().destroy(request, *args, **kwargs)


def _run_workflow(view, request, pk, fn):
    event = Event.objects.filter(pk=pk).first()
    if not event:
        return Response({"success": False, "message": "Event not found."},
                        status=status.HTTP_404_NOT_FOUND)
    try:
        event = fn(event, request.user)
    except PermissionError as exc:
        return Response({"success": False, "message": str(exc)},
                        status=status.HTTP_403_FORBIDDEN)
    except ValueError as exc:
        return Response({"success": False, "message": str(exc)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response({"success": True, "status": event.status,
                     "message": "Transition completed."})


class EventSubmitView(APIView):
    permission_classes = [IsEventManagerOrAdmin]
    def post(self, request, pk):
        return _run_workflow(self, request, pk, EventWorkflowService.submit_event)


class EventApproveView(APIView):
    permission_classes = [IsAdmin]
    def post(self, request, pk):
        return _run_workflow(self, request, pk, EventWorkflowService.approve_event)


class EventRejectView(APIView):
    permission_classes = [IsAdmin]
    def post(self, request, pk):
        event = Event.objects.filter(pk=pk).first()
        if not event:
            return Response({"success": False, "message": "Event not found."},
                            status=status.HTTP_404_NOT_FOUND)
        reason = request.data.get("reason", "").strip()
        try:
            event = EventWorkflowService.reject_event(event, request.user, reason)
        except PermissionError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "status": event.status, "message": "Event rejected."})


class EventStartView(APIView):
    permission_classes = [IsEventManagerOrAdmin]
    def post(self, request, pk):
        return _run_workflow(self, request, pk, EventWorkflowService.start_event)


class EventCompleteView(APIView):
    permission_classes = [IsEventManagerOrAdmin]
    def post(self, request, pk):
        return _run_workflow(self, request, pk, EventWorkflowService.complete_event)


class EventCancelView(APIView):
    permission_classes = [IsEventManagerOrAdmin]
    def post(self, request, pk):
        return _run_workflow(self, request, pk, EventWorkflowService.cancel_event)


urlpatterns = [
    path("events/", EventListCreateView.as_view(), name="api_event_list"),
    path("events/<int:pk>/", EventDetailView.as_view(), name="api_event_detail"),
    path("events/<int:pk>/submit/", EventSubmitView.as_view(), name="api_event_submit"),
    path("events/<int:pk>/approve/", EventApproveView.as_view(), name="api_event_approve"),
    path("events/<int:pk>/reject/", EventRejectView.as_view(), name="api_event_reject"),
    path("events/<int:pk>/start/", EventStartView.as_view(), name="api_event_start"),
    path("events/<int:pk>/complete/", EventCompleteView.as_view(), name="api_event_complete"),
    path("events/<int:pk>/cancel/", EventCancelView.as_view(), name="api_event_cancel"),
]
