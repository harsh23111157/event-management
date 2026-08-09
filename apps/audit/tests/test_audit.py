from django.test import TestCase
from apps.accounts.models import User, Role
from apps.audit.models import AuditLog
from apps.audit.services import AuditService


class AuditTests(TestCase):
    def test_audit_log_creation(self):
        user = User.objects.create_user(
            username="auditor", email="audit@test.com", password="pass", role=Role.ADMIN
        )
        log = AuditService.log(
            user=user, action="TEST_ACTION", entity_type="event", entity_id=42, description="Test audit entry"
        )
        self.assertEqual(log.action, "TEST_ACTION")
        self.assertEqual(log.user, user)
        self.assertEqual(AuditLog.objects.count(), 1)
