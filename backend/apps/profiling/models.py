from django.db import models
from apps.residents.models import Resident


class Household(models.Model):
    household_number = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    head_of_household = models.ForeignKey(
        Resident,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_household',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Household'
        verbose_name_plural = 'Households'

    def __str__(self):
        return f'Household #{self.household_number}'


class FamilyMember(models.Model):
    class Relationship(models.TextChoices):
        HEAD = 'HEAD', 'Head'
        SPOUSE = 'SPOUSE', 'Spouse'
        CHILD = 'CHILD', 'Child'
        PARENT = 'PARENT', 'Parent'
        SIBLING = 'SIBLING', 'Sibling'
        OTHER = 'OTHER', 'Other'

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='members')
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='family_memberships')
    relationship = models.CharField(max_length=10, choices=Relationship.choices, default=Relationship.OTHER)

    class Meta:
        verbose_name = 'Family Member'
        verbose_name_plural = 'Family Members'
        unique_together = ('household', 'resident')

    def __str__(self):
        return f'{self.resident} — {self.get_relationship_display()} of {self.household}'


class PersonalProfile(models.Model):
    class CivilStatus(models.TextChoices):
        SINGLE = 'SINGLE', 'Single'
        MARRIED = 'MARRIED', 'Married'
        WIDOWED = 'WIDOWED', 'Widowed'
        SEPARATED = 'SEPARATED', 'Separated'

    resident = models.OneToOneField(Resident, on_delete=models.CASCADE, related_name='personal_profile')
    civil_status = models.CharField(max_length=10, choices=CivilStatus.choices, blank=True)
    occupation = models.CharField(max_length=150, blank=True)
    nationality = models.CharField(max_length=50, default='Filipino')
    religion = models.CharField(max_length=100, blank=True)
    educational_attainment = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Personal Profile'
        verbose_name_plural = 'Personal Profiles'

    def __str__(self):
        return f'Profile of {self.resident}'
