"""
Migration 0002 — Audit log enhancements
────────────────────────────────────────
1. AuditLog.purok FK (nullable, for purok-scoped STAFF filtering)
2. New Action choices for profiling events and permission changes
3. Composite indexes on (purok, timestamp) and (actor, timestamp)
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_security_stack'),
        ('residents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='purok',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='audit_logs',
                to='residents.purok',
                help_text='Purok where this action occurred. Null for non-profiling events.',
            ),
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('SUPERADMIN_CREATED', 'Super Admin Created'),
                    ('ADMIN_CREATED', 'Admin Created'),
                    ('STAFF_CREATED', 'Staff Created'),
                    ('RESIDENT_ACCOUNT_CREATED', 'Resident Account Created'),
                    ('USER_UPDATED', 'User Updated'),
                    ('USER_DELETED', 'User Deleted'),
                    ('USER_DEACTIVATED', 'User Deactivated'),
                    ('USER_REACTIVATED', 'User Reactivated'),
                    ('LOGIN_SUCCESS', 'Login Success'),
                    ('LOGIN_FAILED', 'Login Failed'),
                    ('LOGOUT', 'Logout'),
                    ('TWO_FA_SETUP', '2FA Setup'),
                    ('TWO_FA_VERIFIED', '2FA Verified'),
                    ('TWO_FA_FAILED', '2FA Failed'),
                    ('PASSWORD_CHANGED', 'Password Changed'),
                    ('EMAIL_VERIFIED', 'Email Verified'),
                    ('RESIDENT_CREATED', 'Resident Record Created'),
                    ('RESIDENT_UPDATED', 'Resident Record Updated'),
                    ('RESIDENT_DELETED', 'Resident Record Deleted'),
                    ('PERMISSION_GRANTED', 'Permission Granted'),
                    ('PERMISSION_REVOKED', 'Permission Revoked'),
                    ('PERMISSION_CHANGED', 'Permission Changed'),
                    ('SURVEY_CREATED', 'Survey Created'),
                    ('SURVEY_UPDATED', 'Survey Updated'),
                    ('SURVEY_SUBMITTED', 'Survey Submitted'),
                    ('SURVEY_VERIFIED', 'Survey Verified'),
                    ('SURVEY_REVISION', 'Survey Sent for Revision'),
                    ('SURVEY_DELETED', 'Survey Deleted'),
                    ('HOUSEHOLD_CREATED', 'Household Created'),
                    ('HOUSEHOLD_UPDATED', 'Household Updated'),
                    ('HOUSEHOLD_DELETED', 'Household Deleted'),
                    ('SCHEMA_CREATED', 'Form Schema Created'),
                    ('SCHEMA_UPDATED', 'Form Schema Updated'),
                    ('SCHEMA_DELETED', 'Form Schema Deleted'),
                    ('RESIDENT_ACCT_LINKED', 'Resident Account Linked to Person'),
                ],
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['purok', 'timestamp'], name='audit_purok_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['actor', 'timestamp'], name='audit_actor_ts_idx'),
        ),
    ]
