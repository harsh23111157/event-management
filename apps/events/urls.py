from django.urls import path

from .views import (EventCreateView, EventDetailView, EventListView,
                    EventUpdateView, EventWorkflowActionView)

urlpatterns = [
    path("", EventListView.as_view(), name="event_list"),
    path("create/", EventCreateView.as_view(), name="event_create"),
    path("<int:pk>/", EventDetailView.as_view(), name="event_detail"),
    path("<int:pk>/edit/", EventUpdateView.as_view(), name="event_edit"),
    path("<int:pk>/<str:action>/", EventWorkflowActionView.as_view(), name="event_workflow"),
]
