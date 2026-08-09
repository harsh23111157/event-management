from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import DashboardService


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        filters = {
            "status": request.query_params.get("status", "").strip(),
            "event_type": request.query_params.get("event_type", "").strip(),
            "venue": request.query_params.get("venue", "").strip(),
            "date_range": request.query_params.get("date_range", "30d").strip(),
        }
        if user.is_admin:
            data = DashboardService.get_admin_dashboard(filters)
        elif user.is_event_manager:
            data = DashboardService.get_manager_dashboard(user, filters)
        elif user.is_staff_member:
            data = DashboardService.get_staff_dashboard(user, filters)
        elif user.is_finance:
            data = DashboardService.get_finance_dashboard(filters)
        else:
            data = DashboardService.get_admin_dashboard(filters)

        # Convert queryset objects in data to serializable dicts if needed
        data["upcoming_events"] = [{"id": e.id, "name": e.name, "status": e.status, "start_date": str(e.start_date)} for e in data.get("upcoming_events", [])]
        data["critical_tasks"] = [{"id": t.id, "title": t.title, "priority": t.priority, "status": t.status, "due_date": str(t.due_date)} for t in data.get("critical_tasks", [])]
        data["recent_activity"] = [{"id": a.id, "action": a.action, "timestamp": str(a.timestamp)} for a in data.get("recent_activity", [])]
        if "pending_approvals" in data:
            data["pending_approvals"] = [{"id": e.id, "name": e.name, "budget": float(e.budget)} for e in data.get("pending_approvals", [])]
        if "pending_approvals_queue" in data:
            data["pending_approvals_queue"] = [{"id": ex.id, "description": ex.description, "amount": float(ex.amount)} for ex in data.get("pending_approvals_queue", [])]
        if "venues" in data:
            del data["venues"]
        if "event_types" in data:
            del data["event_types"]

        return Response(data)


urlpatterns = [
    path("dashboard/", DashboardAPIView.as_view(), name="api_dashboard"),
]
