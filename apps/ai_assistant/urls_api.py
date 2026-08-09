"""REST API for AI assistant."""
from django.urls import path
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import Event
from apps.operations.models import TaskStatus

from .services import OpenRouterService


class AiAssistantAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        event_id = request.data.get("event_id")
        if not event_id:
            return Response({"success": False, "message": "event_id is required."}, status=400)
        event = get_object_or_404(Event, pk=event_id)
        tasks = event.tasks.all()
        event_data = {
            "name": event.name,
            "status": event.status,
            "start_date": str(event.start_date),
            "end_date": str(event.end_date),
            "venue": event.venue.name,
            "venue_capacity": event.venue.capacity,
            "expected_attendees": event.expected_attendees,
            "budget": float(event.budget),
            "manager": event.manager.get_full_name(),
            "total_tasks": tasks.count(),
            "completed_tasks": tasks.filter(status=TaskStatus.COMPLETED).count(),
            "pending_tasks": tasks.exclude(status=TaskStatus.COMPLETED).count(),
        }
        result = OpenRouterService.generate_event_summary(event_data)
        return Response({"success": True, **result})


urlpatterns = [
    path("ai/assistant/", AiAssistantAPIView.as_view(), name="api_ai_assistant"),
]
