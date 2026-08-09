from django.urls import path

from .views import DashboardView, WorkflowGuideView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("workflow/", WorkflowGuideView.as_view(), name="workflow_guide"),
]

