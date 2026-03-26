from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        # Account management
        SUPERADMIN_CREATED = 'SUPERADMIN_CREATED', 'Super Admin Created'
        ADMIN_CREATED = 'ADMIN_CREATED', 'Admin Created'
        STAFF_CREATED = 'STAFF_CREATED', 'Staff Created'
        RESIDENT_ACCOUNT_CREATED = 'RESIDENT_ACCOUNT_CREATED', 'Resident Account Created'
        USER_UPDATED = 'USER_UPDATED', 'User Updated'
        USER_DELETED = 'USER_DELETED', 'User Deleted'
        USER_DEACTIVATED = 'USER_DEACTIVATED', 'User Deactivated'
        USER_REACTIVATED = 'USER_REACTIVATED', 'User Reactivated'
        # Authentication
        LOGIN_SUCCESS = 'LOGIN_SUCCESS', 'Login Success'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Login Failed'
        LOGOUT = 'LOGOUT', 'Logout'
        TWO_FA_SETUP = 'TWO_FA_SETUP', '2FA Setup'
        TWO_FA_VERIFIED = 'TWO_FA_VERIFIED', '2FA Verified'
        TWO_FA_FAILED = 'TWO_FA_FAILED', '2FA Failed'
        # Credentials
        PASSWORD_CHANGED = 'PASSWORD_CHANGED', 'Password Changed'
        EMAIL_VERIFIED = 'EMAIL_VERIFIED', 'Email Verified'
        # Data
        RESIDENT_CREATED = 'RESIDENT_CREATED', 'Resident Record Created'
        RESIDENT_UPDATED = 'RESIDENT_UPDATED', 'Resident Record Updated'
        RESIDENT_DELETED = 'RESIDENT_DELETED', 'Resident Record Deleted'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions',
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        actor = self.actor.email if self.actor else 'System'
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {actor} → {self.action}'
