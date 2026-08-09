from django.urls import path
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from apps.accounts.permissions import IsAdmin
from apps.venues.models import Venue

from .serializers import VenueSerializer


class VenueListCreateView(ListCreateAPIView):
    serializer_class = VenueSerializer
    queryset = Venue.objects.all()

    def create(self, request, *args, **kwargs):
        if not request.user.is_admin:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can create venues.")
        return super().create(request, *args, **kwargs)


class VenueDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = VenueSerializer
    queryset = Venue.objects.all()

    def update(self, request, *args, **kwargs):
        if not request.user.is_admin:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can edit venues.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_admin:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can delete venues.")
        return super().destroy(request, *args, **kwargs)


urlpatterns = [
    path("venues/", VenueListCreateView.as_view(), name="api_venue_list"),
    path("venues/<int:pk>/", VenueDetailView.as_view(), name="api_venue_detail"),
]
