from django.urls import path

from .views import (EventVendorCreateView, VendorCreateView,
                     VendorListView, VendorUpdateView)

urlpatterns = [
    path("", VendorListView.as_view(), name="vendor_list"),
    path("new/", VendorCreateView.as_view(), name="vendor_create"),
    path("create/", VendorCreateView.as_view(), name="vendor_create_alias"),
    path("<int:pk>/edit/", VendorUpdateView.as_view(), name="vendor_edit"),
    path("events/<int:pk>/assign/", EventVendorCreateView.as_view(), name="event_vendor_create"),
]
