from django.urls import path

from .views import VenueCreateView, VenueListView, VenueUpdateView

urlpatterns = [
    path("", VenueListView.as_view(), name="venue_list"),
    path("new/", VenueCreateView.as_view(), name="venue_create"),
    path("create/", VenueCreateView.as_view(), name="venue_create_alias"),
    path("<int:pk>/edit/", VenueUpdateView.as_view(), name="venue_edit"),
]
