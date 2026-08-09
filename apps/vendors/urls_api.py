from django.urls import path
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListCreateAPIView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.vendors.models import EventVendor, Vendor

from .serializers import EventVendorSerializer, VendorSerializer


class VendorListCreateView(ListCreateAPIView):
    serializer_class = VendorSerializer
    queryset = Vendor.objects.all()

    def create(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only event managers or admins can create vendors.")
        return super().create(request, *args, **kwargs)


class EventVendorListCreateView(ListCreateAPIView):
    serializer_class = EventVendorSerializer
    queryset = EventVendor.objects.select_related("event", "vendor")

    def create(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request.user):
            raise PermissionDenied("Only event managers or admins can assign vendors.")
        return super().create(request, *args, **kwargs)


urlpatterns = [
    path("vendors/", VendorListCreateView.as_view(), name="api_vendor_list"),
    path("event-vendors/", EventVendorListCreateView.as_view(), name="api_event_vendor_list"),
]
