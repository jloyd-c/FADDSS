"""
Migration 0006 — RBAC enhancements
────────────────────────────────────
1. StaffPurokPermission.can_view_audit_logs  (new field)
2. User.person                              (nullable FK → profiling.Person for RESIDENT accounts)
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_security_stack'),
        ('profiling', '0001_initial'),
    ]

    operations = [
        # ── 1. StaffPurokPermission: add can_view_audit_logs ──────────────────
        migrations.AddField(
            model_name='staffpurokpermission',
            name='can_view_audit_logs',
            field=models.BooleanField(
                default=False,
                help_text='Staff can view audit logs scoped to this purok only.',
            ),
        ),

        # ── 2. User: add nullable person FK ──────────────────────────────────
        migrations.AddField(
            model_name='user',
            name='person',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='user_account',
                to='profiling.person',
                help_text='Links a RESIDENT user to their Person record in the profiling DB. '
                          'Null for STAFF, ADMIN, and SUPER_ADMIN.',
            ),
        ),
    ]
