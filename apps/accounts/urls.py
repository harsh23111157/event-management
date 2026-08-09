"""Web (session) URLs for accounts."""
from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.EventOpsLoginView.as_view(), name="login"),
    path("logout/", views.EventOpsLogoutView.as_view(), name="logout"),
    path("users/", views.UserListView.as_view(), name="users"),
    path("users/new/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_edit"),
]
