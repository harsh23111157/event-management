"""Web view for the AI assistant."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.events.models import Event
from apps.operations.models import EventTask, TaskStatus

from .services import OpenRouterService


class AiAssistantView(LoginRequiredMixin, View):
    template_name = "ai_assistant/assistant.html"

    def _get_accessible_events(self, user):
        qs = Event.objects.select_related("venue", "manager").order_by("name")
        if user.is_staff_member:
            qs = qs.filter(staff_assignments__staff=user).distinct()
        elif user.is_event_manager:
            qs = qs.filter(manager=user)
        return qs

    def get(self, request):
        events = self._get_accessible_events(request.user)
        selected_event_id = request.GET.get("event_id")
        return render(request, self.template_name, {
            "events": events,
            "selected_event_id": int(selected_event_id) if selected_event_id and selected_event_id.isdigit() else None,
            "result": None,
            "is_configured": OpenRouterService.is_configured(),
        })

    def post(self, request):
        events = self._get_accessible_events(request.user)
        event_id = request.POST.get("event_id")
        result = None
        selected_event = None
        if event_id:
            event = get_object_or_404(self._get_accessible_events(request.user), pk=event_id)
            selected_event = event
            tasks = event.tasks.all()
            expenses = event.expenses.all()
            approved_exp = sum(e.amount for e in expenses if e.status == "APPROVED")
            event_data = {
                "name": event.name,
                "status": event.status,
                "event_type": event.get_event_type_display(),
                "start_date": str(event.start_date),
                "end_date": str(event.end_date),
                "venue": event.venue.name,
                "venue_capacity": event.venue.capacity,
                "expected_attendees": event.expected_attendees,
                "budget": float(event.budget) if event.budget else 0.0,
                "approved_expenses": float(approved_exp) if approved_exp else 0.0,
                "manager": event.manager.get_full_name() or event.manager.username,
                "total_tasks": tasks.count(),
                "completed_tasks": tasks.filter(status=TaskStatus.COMPLETED).count(),
                "critical_tasks_pending": tasks.filter(priority="CRITICAL").exclude(status=TaskStatus.COMPLETED).count(),
                "staff_count": event.staff_assignments.count(),
                "vendor_count": event.vendor_assignments.count(),
            }
            result = OpenRouterService.generate_event_summary(event_data, role=request.user.role)
        return render(request, self.template_name, {
            "events": events,
            "selected_event": selected_event,
            "selected_event_id": int(event_id) if event_id and event_id.isdigit() else None,
            "result": result,
            "is_configured": OpenRouterService.is_configured(),
        })
