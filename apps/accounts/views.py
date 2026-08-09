"""Web (session) views for authentication and user management."""
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import LoginForm, UserForm
from .models import Role, User


class EventOpsLoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        from apps.audit.services import AuditService
        AuditService.log(self.request.user, "LOGIN", "user", self.request.user.id, "User logged in")
        return response


class EventOpsLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from apps.audit.services import AuditService
            AuditService.log(request.user, "LOGOUT", "user", request.user.id, "User logged out")
        return super().dispatch(request, *args, **kwargs)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = UserForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("users")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.audit.services import AuditService
        response = super().form_valid(form)
        AuditService.log(self.request.user, "USER_CREATE", "user", self.object.id, f"Created user {self.object.username}")
        messages.success(self.request, f"User {self.object.username} created.")
        return response


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("users")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        old_role = self.get_object().role
        response = super().form_valid(form)
        from apps.audit.services import AuditService
        if old_role != self.object.role:
            AuditService.log(self.request.user, "USER_ROLE_CHANGE", "user", self.object.id,
                             f"Role changed {old_role} -> {self.object.role}")
        AuditService.log(self.request.user, "USER_UPDATE", "user", self.object.id, f"Updated user {self.object.username}")
        messages.success(self.request, f"User {self.object.username} updated.")
        return response


def handler400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def handler404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def handler500(request):
    return render(request, "errors/500.html", status=500)
