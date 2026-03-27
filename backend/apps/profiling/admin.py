from django.contrib import admin
from .models import (
    FormSchema, FieldMapping,
    Household, HouseholdSurvey, Family, Person,
    ProgramAvailed, NormalizedData, HouseholdChangeLog,
)


@admin.register(FormSchema)
class FormSchemaAdmin(admin.ModelAdmin):
    list_display    = ('name', 'year', 'version', 'is_active', 'created_at')
    list_filter     = ('year', 'is_active')
    search_fields   = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(FieldMapping)
class FieldMappingAdmin(admin.ModelAdmin):
    list_display  = ('canonical_name', 'label', 'level', 'data_type')
    list_filter   = ('level', 'data_type')
    search_fields = ('canonical_name', 'label')


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display    = ('household_number', 'purok', 'status', 'is_deleted', 'created_at')
    list_filter     = ('status', 'is_deleted', 'purok')
    search_fields   = ('household_number', 'address')
    readonly_fields = ('id', 'created_at', 'updated_at')

    def get_queryset(self, request):
        # Show ALL records (including deleted) in admin
        return Household.all_objects.all()


@admin.register(HouseholdSurvey)
class HouseholdSurveyAdmin(admin.ModelAdmin):
    list_display    = ('household', 'survey_year', 'status', 'surveyed_by', 'is_deleted')
    list_filter     = ('survey_year', 'status', 'is_deleted')
    search_fields   = ('household__household_number',)
    readonly_fields = ('id', 'created_at', 'updated_at')

    def get_queryset(self, request):
        return HouseholdSurvey.all_objects.select_related('household', 'form_schema')


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display  = ('household_survey', 'family_number', 'monthly_income_bracket', 'is_deleted')
    list_filter   = ('monthly_income_bracket', 'is_deleted')
    readonly_fields = ('id',)

    def get_queryset(self, request):
        return Family.all_objects.select_related('household_survey__household')


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'role', 'gender', 'educational_attainment',
                     'is_registered_voter', 'is_deleted')
    list_filter   = ('role', 'gender', 'educational_attainment', 'civil_status', 'is_deleted')
    search_fields = ('first_name', 'last_name', 'middle_name')
    readonly_fields = ('id', 'created_at', 'updated_at')

    def get_queryset(self, request):
        return Person.all_objects.all()


@admin.register(ProgramAvailed)
class ProgramAvailedAdmin(admin.ModelAdmin):
    list_display  = ('program_type', 'program_name', 'family', 'date_availed', 'amount', 'is_deleted')
    list_filter   = ('program_type', 'is_deleted')
    search_fields = ('program_name', 'reference_no')

    def get_queryset(self, request):
        return ProgramAvailed.all_objects.all()


@admin.register(NormalizedData)
class NormalizedDataAdmin(admin.ModelAdmin):
    list_display  = ('canonical_name', 'canonical_value', 'raw_value', 'survey_year', 'level')
    list_filter   = ('survey_year', 'level', 'canonical_name')
    search_fields = ('canonical_name', 'canonical_value')


@admin.register(HouseholdChangeLog)
class HouseholdChangeLogAdmin(admin.ModelAdmin):
    list_display    = ('household', 'target_type', 'action', 'changed_by',
                       'survey_year', 'changed_at')
    list_filter     = ('target_type', 'action', 'survey_year')
    search_fields   = ('household__household_number',)
    readonly_fields = ('changed_at',)
