from django.contrib import admin
from .models import Household, FamilyMember, PersonalProfile


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ('household_number', 'head_of_household', 'address', 'created_at')
    search_fields = ('household_number', 'address')


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ('resident', 'household', 'relationship')
    list_filter = ('relationship',)


@admin.register(PersonalProfile)
class PersonalProfileAdmin(admin.ModelAdmin):
    list_display = ('resident', 'civil_status', 'occupation', 'nationality')
    search_fields = ('resident__user__email',)
