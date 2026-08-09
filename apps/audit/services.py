"""AuditService — central place to record audit entries."""
from .models import AuditLog


class AuditService:
    @staticmethod
    def log(user, action: str, entity_type: str = "", entity_id: int | None = None,
            description: str = "") -> AuditLog | None:
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        return AuditLog.objects.create(
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
        )
