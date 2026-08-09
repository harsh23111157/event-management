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


def _extract_user(user_or_request):
    return getattr(user_or_request, "user", user_or_request)


def is_admin(user_or_request) -> bool:
    u = _extract_user(user_or_request)
    return bool(u and getattr(u, "is_authenticated", False) and getattr(u, "is_admin", False))


def is_event_manager_or_admin(user_or_request) -> bool:
    u = _extract_user(user_or_request)
    return bool(u and getattr(u, "is_authenticated", False) and (getattr(u, "is_admin", False) or getattr(u, "is_event_manager", False)))


def is_finance_or_admin(user_or_request) -> bool:
    u = _extract_user(user_or_request)
    return bool(u and getattr(u, "is_authenticated", False) and (getattr(u, "is_admin", False) or getattr(u, "is_finance", False)))
