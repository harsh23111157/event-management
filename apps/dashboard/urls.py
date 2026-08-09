from django.urls import path

from .views import AiBriefingView, DashboardView, WorkflowGuideView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("workflow/", WorkflowGuideView.as_view(), name="workflow_guide"),
    path("ai-briefing/", AiBriefingView.as_view(), name="ai_briefing"),
]
