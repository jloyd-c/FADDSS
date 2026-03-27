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
        # Permissions
        PERMISSION_GRANTED  = 'PERMISSION_GRANTED',  'Permission Granted'
        PERMISSION_REVOKED  = 'PERMISSION_REVOKED',  'Permission Revoked'
        PERMISSION_CHANGED  = 'PERMISSION_CHANGED',  'Permission Changed'
        # Profiling — surveys
        SURVEY_CREATED      = 'SURVEY_CREATED',      'Survey Created'
        SURVEY_UPDATED      = 'SURVEY_UPDATED',      'Survey Updated'
        SURVEY_SUBMITTED    = 'SURVEY_SUBMITTED',    'Survey Submitted'
        SURVEY_VERIFIED     = 'SURVEY_VERIFIED',     'Survey Verified'
        SURVEY_REVISION     = 'SURVEY_REVISION',     'Survey Sent for Revision'
        SURVEY_DELETED      = 'SURVEY_DELETED',      'Survey Deleted'
        # Profiling — households
        HOUSEHOLD_CREATED   = 'HOUSEHOLD_CREATED',  'Household Created'
        HOUSEHOLD_UPDATED   = 'HOUSEHOLD_UPDATED',  'Household Updated'
        HOUSEHOLD_DELETED   = 'HOUSEHOLD_DELETED',  'Household Deleted'
        # Profiling — schemas
        SCHEMA_CREATED      = 'SCHEMA_CREATED',     'Form Schema Created'
        SCHEMA_UPDATED      = 'SCHEMA_UPDATED',     'Form Schema Updated'
        SCHEMA_DELETED      = 'SCHEMA_DELETED',     'Form Schema Deleted'
        # Profiling — resident account linking
        RESIDENT_ACCOUNT_LINKED = 'RESIDENT_ACCT_LINKED', 'Resident Account Linked to Person'

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
    # Purok context — set for profiling actions (survey/household events).
    # NULL for system-level events (login, user creation, etc.).
    # Denormalized at write time so STAFF can filter logs by their puroks
    # without chasing FK chains.
    purok = models.ForeignKey(
        'residents.Purok',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        help_text='Purok where this action occurred. Null for non-profiling events.',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['purok', 'timestamp']),
            models.Index(fields=['actor', 'timestamp']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        actor = self.actor.email if self.actor else 'System'
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {actor} → {self.action}'
