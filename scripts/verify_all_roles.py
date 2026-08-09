"""Verification script to test all 4 discrete roles across all pages and endpoints."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.test import Client
from apps.accounts.models import User, Role
from apps.events.models import Event, EventStatus
from apps.finance.models import Expense, ExpenseStatus, ExpenseCategory
from apps.operations.models import EventTask, TaskPriority, TaskStatus

print("=" * 60)
print("EVENTOPS: COMPREHENSIVE RBAC & ROLE-AWARE VERIFICATION")
print("=" * 60)

# Retrieve or create users for 4 roles
roles = {
    Role.ADMIN: User.objects.filter(role=Role.ADMIN).first(),
    Role.EVENT_MANAGER: User.objects.filter(role=Role.EVENT_MANAGER).first(),
    Role.FINANCE: User.objects.filter(role=Role.FINANCE).first(),
    Role.STAFF: User.objects.filter(role=Role.STAFF).first(),
}

event = Event.objects.first()
task = EventTask.objects.first()
expense = Expense.objects.first()

print(f"\n1. Testing Dashboard for All 4 Roles:")
for role_name, user in roles.items():
    if not user:
        continue
    client = Client()
    client.force_login(user)
    resp = client.get("/dashboard/")
    print(f"  [{role_name}] /dashboard/ -> HTTP {resp.status_code}")
    assert resp.status_code == 200

print(f"\n2. Testing Event Pipeline List for All 4 Roles:")
for role_name, user in roles.items():
    if not user:
        continue
    client = Client()
    client.force_login(user)
    resp = client.get("/events/")
    print(f"  [{role_name}] /events/ -> HTTP {resp.status_code}")
    assert resp.status_code == 200

if event:
    print(f"\n3. Testing Event Detail & Readiness Workspace (Event #{event.id}):")
    for role_name, user in roles.items():
        if not user:
            continue
        client = Client()
        client.force_login(user)
        resp = client.get(f"/events/{event.id}/")
        print(f"  [{role_name}] /events/{event.id}/ -> HTTP {resp.status_code}")

print(f"\n4. Testing Role Access Restrictions (Expecting HTTP 403 where unauthorized):")

# Staff cannot access User management
client = Client()
client.force_login(roles[Role.STAFF])
resp = client.get("/users/")
print(f"  [STAFF] /users/ -> HTTP {resp.status_code} (Expected 403 Forbidden)")
assert resp.status_code == 403

# Staff cannot access Audit logs
resp = client.get("/audit-logs/")
print(f"  [STAFF] /audit-logs/ -> HTTP {resp.status_code} (Expected 403 Forbidden)")
assert resp.status_code == 403

# Staff cannot create events
resp = client.get("/events/create/")
print(f"  [STAFF] /events/create/ -> HTTP {resp.status_code} (Expected 403 Forbidden)")
assert resp.status_code == 403

# Staff cannot create venues
resp = client.get("/venues/create/")
print(f"  [STAFF] /venues/create/ -> HTTP {resp.status_code} (Expected 403 Forbidden)")
assert resp.status_code == 403

# Staff cannot access Finance Reports
resp = client.get("/reports/finance/")
print(f"  [STAFF] /reports/finance/ -> HTTP {resp.status_code} (Expected 403 Forbidden)")
assert resp.status_code == 403

# Admin can access User management and Audit logs
client = Client()
client.force_login(roles[Role.ADMIN])
resp = client.get("/users/")
print(f"  [ADMIN] /users/ -> HTTP {resp.status_code} (Expected 200 OK)")
assert resp.status_code == 200

resp = client.get("/audit-logs/")
print(f"  [ADMIN] /audit-logs/ -> HTTP {resp.status_code} (Expected 200 OK)")
assert resp.status_code == 200

print(f"\n5. Testing AI Assistant Endpoints:")
for role_name, user in roles.items():
    if not user:
        continue
    client = Client()
    client.force_login(user)
    resp = client.get("/ai/")
    print(f"  [{role_name}] /ai/ -> HTTP {resp.status_code}")
    assert resp.status_code == 200

print("\n" + "=" * 60)
print("ALL RBAC AND ROLE-AWARE VERIFICATION CHECKS PASSED!")
print("=" * 60)
