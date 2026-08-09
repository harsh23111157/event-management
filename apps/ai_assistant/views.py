"""Web view for the AI assistant."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.events.models import Event
from apps.operations.models import EventTask, TaskStatus

from .services import OpenRouterService


class AiAssistantView(LoginRequiredMixin, View):
    template_name = "ai_assistant/assistant.html"

    def get(self, request):
        events = Event.objects.order_by("name")
        return render(request, self.template_name, {"events": events, "result": None})

    def post(self, request):
        event_id = request.POST.get("event_id")
        events = Event.objects.order_by("name")
        result = None
        if event_id:
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
                "staff_count": event.staff_assignments.count(),
                "vendor_count": event.vendor_assignments.count(),
            }
            result = OpenRouterService.generate_event_summary(event_data)
        return render(request, self.template_name, {"events": events, "result": result})
