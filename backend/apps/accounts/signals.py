from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='accounts.User')
def log_superadmin_creation(sender, instance, created, **kwargs):
    """Auto-log whenever a SUPER_ADMIN account is created (always via CLI)."""
    if created and instance.role == 'SUPER_ADMIN':
        try:
            from apps.audit.models import AuditLog
            from apps.audit.utils import log_action
            log_action(
                action=AuditLog.Action.SUPERADMIN_CREATED,
                actor=None,  # CLI — no web actor
                target_user=instance,
                extra={'email': instance.email, 'method': 'command_line'},
            )
        except Exception:
            # Never let audit logging crash user creation.
            pass
