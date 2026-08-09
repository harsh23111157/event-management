"""Role-based permission helpers shared across the app."""
from rest_framework import permissions

from .models import Role


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsEventManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_admin or u.is_event_manager))


class IsFinanceOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_admin or u.is_finance))


class IsStaffOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in (Role.ADMIN, Role.EVENT_MANAGER, Role.STAFF))


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.is_admin)


def is_event_manager_or_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_admin or user.is_event_manager))


def is_finance_or_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_admin or user.is_finance))
