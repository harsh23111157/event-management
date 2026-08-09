from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
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
    paginate_by = 12

    def get_queryset(self):
        qs = Vendor.objects.annotate(
            event_count=Count("event_assignments"),
            total_contracts=Sum("event_assignments__contract_amount")
        )
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(service_type__icontains=search) | Q(contact_person__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_create_vendor"] = self.request.user.is_admin or self.request.user.is_event_manager
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class VendorCreateView(LoginRequiredMixin, CreateView):
    model = Vendor
    form_class = VendorForm
    template_name = "vendors/vendor_form.html"
    success_url = reverse_lazy("vendor_list")

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_event_manager):
            raise PermissionDenied("Only Administrators and Event Managers can create vendors.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.audit.services import AuditService
        vendor = form.save()
        AuditService.log(self.request.user, "VENDOR_CREATE", "vendor", vendor.id, f"Created vendor '{vendor.name}'")
        messages.success(self.request, f"Vendor '{vendor.name}' created successfully.")
        return super().form_valid(form)


class VendorUpdateView(LoginRequiredMixin, UpdateView):
    model = Vendor
    form_class = VendorForm
    template_name = "vendors/vendor_form.html"
    success_url = reverse_lazy("vendor_list")

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_event_manager):
            raise PermissionDenied("Only Administrators and Event Managers can edit vendors.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.audit.services import AuditService
        vendor = form.save()
        AuditService.log(self.request.user, "VENDOR_UPDATE", "vendor", vendor.id, f"Updated vendor '{vendor.name}'")
        messages.success(self.request, f"Vendor '{vendor.name}' updated successfully.")
        return super().form_valid(form)


class EventVendorCreateView(LoginRequiredMixin, CreateView):
    model = EventVendor
    form_class = EventVendorForm
    template_name = "vendors/eventvendor_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=kwargs["pk"])
        user = request.user
        if not (user.is_admin or (user.is_event_manager and self.event.manager_id == user.id)):
            raise PermissionDenied("You can only assign vendors to events you manage.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.event
        return ctx

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["event"] = self.event
        return kw

    def form_valid(self, form):
        from apps.audit.services import AuditService
        assignment = form.save()
        AuditService.log(self.request.user, "VENDOR_ASSIGN", "eventvendor", assignment.id,
                         f"Assigned vendor {assignment.vendor.name} to {self.event.name}")
        messages.success(self.request, f"Vendor '{assignment.vendor.name}' assigned to event.")
        return redirect("event_detail", pk=self.event.id)
