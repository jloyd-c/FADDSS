from django.db import models
from django.core.validators import RegexValidator
from apps.accounts.models import User


class Resident(models.Model):
    """
    Resident model - stores census-like data for barangay residents
    """
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    CIVIL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
        ('divorced', 'Divorced'),
    ]
    
    EMPLOYMENT_STATUS_CHOICES = [
        ('employed', 'Employed'),
        ('unemployed', 'Unemployed'),
        ('self_employed', 'Self-Employed'),
        ('student', 'Student'),
        ('retired', 'Retired'),
    ]
    
    # Primary Information
    resident_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Auto-generated resident ID"
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=10, blank=True, help_text="Jr., Sr., III, etc.")
    
    # Personal Details
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    civil_status = models.CharField(max_length=20, choices=CIVIL_STATUS_CHOICES)
    
    # Contact Information
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be 9-15 digits. Can start with +"
    )
    phone_number = models.CharField(
        validators=[phone_validator],
        max_length=17,
        blank=True
    )
    email = models.EmailField(blank=True)
    
    # Address
    purok = models.CharField(max_length=50, help_text="Purok/Zone number")
    street = models.CharField(max_length=200)
    
    # Additional Information
    is_pwd = models.BooleanField(
        default=False,
        verbose_name='Person with Disability'
    )
    is_senior = models.BooleanField(
        default=False,
        verbose_name='Senior Citizen (60+)'
    )
    is_4ps = models.BooleanField(
        default=False,
        verbose_name='4Ps Beneficiary'
    )
    
    # Employment
    employment_status = models.CharField(
        max_length=50,
        choices=EMPLOYMENT_STATUS_CHOICES,
        blank=True
    )
    occupation = models.CharField(max_length=100, blank=True)
    
    # Portal Account Status
    has_portal_account = models.BooleanField(
        default=False,
        help_text="Has resident portal account created"
    )
    
    # Meta Information
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='residents_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'residents'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['purok']),
        ]
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.resident_id})"
    
    def get_full_name(self):
        """Returns full name with middle name and suffix"""
        parts = [self.first_name, self.middle_name, self.last_name, self.suffix]
        return ' '.join(filter(None, parts))
    
    def age(self):
        """Calculate age from date of birth"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def full_address(self):
        """Returns formatted full address"""
        return f"{self.street}, Purok {self.purok}"
    
    def save(self, *args, **kwargs):
        """Auto-generate resident_id if not provided"""
        if not self.resident_id:
            # Get the last resident ID
            last_resident = Resident.objects.all().order_by('id').last()
            if last_resident:
                last_id = int(last_resident.resident_id.split('-')[1])
                new_id = last_id + 1
            else:
                new_id = 1
            
            # Format: RES-0001, RES-0002, etc.
            self.resident_id = f'RES-{new_id:04d}'
        
        super().save(*args, **kwargs)