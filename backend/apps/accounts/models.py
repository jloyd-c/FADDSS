import datetime
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        STAFF = 'STAFF', 'Staff'
        RESIDENT = 'RESIDENT', 'Resident'

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.RESIDENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Account lifecycle
    created_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users'
    )
    must_change_password = models.BooleanField(default=False)
    require_2fa = models.BooleanField(default=False)

    # Email & 2FA
    email_verified = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_enabled = models.BooleanField(default=False)

    # Granular permissions
    perm_manage_residents = models.BooleanField(default=False)
    perm_manage_staff = models.BooleanField(default=False)
    perm_view_reports = models.BooleanField(default=False)
    perm_delete_users = models.BooleanField(default=False)
    perm_change_system_settings = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_admin(self):
        return self.role in (self.Role.ADMIN, self.Role.SUPER_ADMIN)

    @property
    def is_barangay_staff(self):
        return self.role == self.Role.STAFF

    @property
    def is_resident_user(self):
        return self.role == self.Role.RESIDENT


class StaffProfile(models.Model):
    class Department(models.TextChoices):
        HEALTH = 'HEALTH', 'Health Services'
        SOCIAL = 'SOCIAL', 'Social Services'
        RECORDS = 'RECORDS', 'Records Management'
        SECURITY = 'SECURITY', 'Security & Peace Order'
        ENVIRONMENT = 'ENVIRONMENT', 'Environment & Sanitation'
        LIVELIHOOD = 'LIVELIHOOD', 'Livelihood & Employment'
        GENERAL = 'GENERAL', 'General Services'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile',
    )
    phone = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=15, choices=Department.choices, blank=True)

    # Access schedule
    work_start = models.TimeField(default=datetime.time(8, 0))
    work_end = models.TimeField(default=datetime.time(17, 0))
    allow_weekend = models.BooleanField(default=False)
    allow_after_hours = models.BooleanField(default=False)

    # Global staff permissions (not purok-specific)
    perm_generate_reports = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

    def __str__(self):
        return f'{self.user.full_name} ({self.get_department_display()})'


class StaffPurokPermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purok_permissions',
    )
    purok = models.ForeignKey(
        'residents.Purok',
        on_delete=models.CASCADE,
        related_name='staff_permissions',
    )
    can_view = models.BooleanField(default=True)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'purok')
        verbose_name = 'Staff Purok Permission'
        verbose_name_plural = 'Staff Purok Permissions'

    def __str__(self):
        return f'{self.user.email} → {self.purok}'


class EmailVerification(models.Model):
    """Token sent to a new admin so they can verify their email address."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'

    def __str__(self):
        return f'Verification for {self.user.email}'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.verified_at is not None

    def mark_verified(self):
        self.verified_at = timezone.now()
        self.save(update_fields=['verified_at'])
        self.user.email_verified = True
        self.user.save(update_fields=['email_verified'])


class AdminIPWhitelist(models.Model):
    """Optional IP address restrictions for ADMIN and SUPER_ADMIN accounts."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ip_whitelist',
    )
    ip_address = models.GenericIPAddressField()
    label = models.CharField(max_length=100, blank=True, help_text='e.g. "Office", "Home"')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_ip_whitelists',
    )

    class Meta:
        unique_together = ('user', 'ip_address')
        verbose_name = 'Admin IP Whitelist'
        verbose_name_plural = 'Admin IP Whitelists'

    def __str__(self):
        return f'{self.user.email} — {self.ip_address} ({self.label})'
