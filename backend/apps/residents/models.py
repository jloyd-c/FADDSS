from django.conf import settings
from django.db import models


class Purok(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['number']
        verbose_name = 'Purok'
        verbose_name_plural = 'Puroks'

    def __str__(self):
        label = f'Purok {self.number}'
        return f'{label} - {self.name}' if self.name else label


class Resident(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        DECEASED = 'DECEASED', 'Deceased'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'

    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    class CivilStatus(models.TextChoices):
        SINGLE = 'SINGLE', 'Single'
        MARRIED = 'MARRIED', 'Married'
        WIDOWED = 'WIDOWED', 'Widowed'
        SEPARATED = 'SEPARATED', 'Separated'
        ANNULLED = 'ANNULLED', 'Annulled'

    # User account — optional until resident requests portal access.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resident_profile',
    )
    purok = models.ForeignKey(
        Purok,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='residents',
    )

    # Personal information
    first_name = models.CharField(max_length=150, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    civil_status = models.CharField(max_length=10, choices=CivilStatus.choices, blank=True)

    # Contact
    contact_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)

    # Record info
    resident_id = models.CharField(max_length=20, unique=True, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Resident'
        verbose_name_plural = 'Residents'
        ordering = ['-created_at']

    def __str__(self):
        full_name = ' '.join(filter(None, [self.first_name, self.middle_name, self.last_name]))
        return f'{full_name} ({self.resident_id})' if self.resident_id else full_name

    @property
    def full_name(self):
        return ' '.join(filter(None, [self.first_name, self.middle_name, self.last_name]))

    @property
    def has_account(self):
        return self.user_id is not None
