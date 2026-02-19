from django.contrib import admin
from .models import Resident
from .models import Household


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = [
        'resident_id', 
        'last_name', 
        'first_name', 
        'age', 
        'gender', 
        'purok', 
        'is_active'
    ]
    list_filter = ['gender', 'civil_status', 'purok', 'is_pwd', 'is_senior', 'is_active']
    search_fields = ['resident_id', 'first_name', 'last_name', 'phone_number']
    readonly_fields = ['resident_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('resident_id', 'first_name', 'middle_name', 'last_name', 'suffix')
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'gender', 'civil_status')
        }),
        ('Contact', {
            'fields': ('phone_number', 'email')
        }),
        ('Address', {
            'fields': ('purok', 'street')
        }),
        ('Additional Info', {
            'fields': ('is_pwd', 'is_senior', 'is_4ps', 'employment_status', 'occupation')
        }),
        ('Meta', {
            'fields': ('is_active', 'has_portal_account', 'notes', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = [
        'household_id',
        'household_head',
        'purok',
        'housing_type',
        'member_count',
        'is_active'
    ]
    list_filter = ['housing_type', 'housing_condition', 'purok', 'is_active']
    search_fields = ['household_id', 'street', 'purok']
    readonly_fields = ['household_id', 'created_at', 'updated_at']