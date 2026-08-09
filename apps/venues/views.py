from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import VenueForm
from .models import Venue


class VenueListView(LoginRequiredMixin, ListView):
    model = Venue
    template_name = "venues/venue_list.html"
    context_object_name = "venues"
    paginate_by = 12

    def get_queryset(self):
        qs = Venue.objects.annotate(active_events_count=Count("events", filter=~Q(events__status="CANCELLED")))
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(address__icontains=search) | Q(contact_person__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_create_venue"] = self.request.user.is_admin
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class VenueCreateView(LoginRequiredMixin, CreateView):
    model = Venue
    form_class = VenueForm
    template_name = "venues/venue_form.html"
    success_url = reverse_lazy("venue_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("Only Administrators can create venues.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.audit.services import AuditService
        venue = form.save()
        AuditService.log(self.request.user, "VENUE_CREATE", "venue", venue.id, f"Created venue '{venue.name}'")
        messages.success(self.request, f"Venue '{venue.name}' created successfully.")
        return super().form_valid(form)


class VenueUpdateView(LoginRequiredMixin, UpdateView):
    model = Venue
    form_class = VenueForm
    template_name = "venues/venue_form.html"
    success_url = reverse_lazy("venue_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("Only Administrators can edit venues.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.audit.services import AuditService
        venue = form.save()
        AuditService.log(self.request.user, "VENUE_UPDATE", "venue", venue.id, f"Updated venue '{venue.name}'")
        messages.success(self.request, f"Venue '{venue.name}' updated successfully.")
        return super().form_valid(form)
