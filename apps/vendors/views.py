from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.permissions import is_event_manager_or_admin
from apps.events.models import Event

from .forms import EventVendorForm, VendorForm
from .models import EventVendor, Vendor


class VendorListView(LoginRequiredMixin, ListView):
    model = Vendor
    template_name = "vendors/vendor_list.html"
    context_object_name = "vendors"


class VendorCreateView(LoginRequiredMixin, CreateView):
    model = Vendor
    form_class = VendorForm
    template_name = "vendors/vendor_form.html"
    success_url = reverse_lazy("vendor_list")

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Vendor '{form.instance.name}' created.")
        return super().form_valid(form)


class VendorUpdateView(LoginRequiredMixin, UpdateView):
    model = Vendor
    form_class = VendorForm
    template_name = "vendors/vendor_form.html"
    success_url = reverse_lazy("vendor_list")

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class EventVendorCreateView(LoginRequiredMixin, CreateView):
    model = EventVendor
    form_class = EventVendorForm
    template_name = "vendors/eventvendor_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_event_manager_or_admin(request):
            return redirect("dashboard")
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.event
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        assignment = form.save()
        AuditService.log(self.request.user, "VENDOR_ASSIGN", "eventvendor", assignment.id,
                         f"Assigned vendor {assignment.vendor} to {self.event.name}")
        messages.success(self.request, "Vendor assigned to event.")
        return redirect("event_detail", pk=self.event.id)
