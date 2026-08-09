from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import VenueForm
from .models import Venue


class VenueListView(LoginRequiredMixin, ListView):
    model = Venue
    template_name = "venues/venue_list.html"
    context_object_name = "venues"


class VenueCreateView(LoginRequiredMixin, CreateView):
    model = Venue
    form_class = VenueForm
    template_name = "venues/venue_form.html"
    success_url = reverse_lazy("venue_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Venue '{form.instance.name}' created.")
        return super().form_valid(form)


class VenueUpdateView(LoginRequiredMixin, UpdateView):
    model = Venue
    form_class = VenueForm
    template_name = "venues/venue_form.html"
    success_url = reverse_lazy("venue_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Venue '{form.instance.name}' updated.")
        return super().form_valid(form)
