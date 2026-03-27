"""
Profiling App — Serializers (Phase 2)
══════════════════════════════════════════════════════════════════════════════

SERIALIZER PAIRS
────────────────
Most domain objects have two serializers:
  - *Serializer      — read (GET), uses nested sub-serializers, includes computed fields
  - *WriteSerializer — write (POST/PATCH), flat or lightly-nested, validates input

NESTED WRITE PATTERN
────────────────────
CreateSurveySerializer is the ONLY place that does nested writes. It validates
the full input structure (survey + families + persons + programs) and delegates
ALL creation to HouseholdService.create_survey(). It does NOT call
nested ModelSerializer.create() — that would bypass the service's atomicity
and change-logging guarantees.

CHANGE LOG
──────────
Serializers must NEVER call HouseholdChangeLog directly.
All logging happens in services.py.
"""

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import (
    Family, FieldMapping, FormSchema, Household,
    HouseholdChangeLog, HouseholdSurvey, NormalizedData, Person,
    ProgramAvailed,
)
from .services import HouseholdService, SurveyAlreadyExistsError


# ─────────────────────────────────────────────────────────────────────────────
# FormSchema / FieldMapping
# ─────────────────────────────────────────────────────────────────────────────

class FieldMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model   = FieldMapping
        fields  = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class FormSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model   = FormSchema
        fields  = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class FormSchemaLightSerializer(serializers.ModelSerializer):
    """Compact representation — used as a nested FK inside survey responses."""
    class Meta:
        model  = FormSchema
        fields = ('id', 'year', 'version', 'name', 'is_active')


# ─────────────────────────────────────────────────────────────────────────────
# ProgramAvailed
# ─────────────────────────────────────────────────────────────────────────────

class ProgramAvailedSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.SerializerMethodField()

    class Meta:
        model  = ProgramAvailed
        fields = (
            'id', 'family', 'beneficiary', 'beneficiary_name',
            'program_type', 'program_name', 'date_availed',
            'amount', 'reference_no', 'description', 'data',
            'is_deleted', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'beneficiary_name')

    def get_beneficiary_name(self, obj):
        return obj.beneficiary.full_name if obj.beneficiary else None


class ProgramAvailedWriteSerializer(serializers.ModelSerializer):
    """
    Used when creating/updating a ProgramAvailed directly (not nested in survey).
    beneficiary_index is only supported in the nested-create path (CreateSurveySerializer).
    """
    class Meta:
        model   = ProgramAvailed
        fields  = (
            'family', 'beneficiary',
            'program_type', 'program_name', 'date_availed',
            'amount', 'reference_no', 'description', 'data',
        )


# ─────────────────────────────────────────────────────────────────────────────
# Person
# ─────────────────────────────────────────────────────────────────────────────

class PersonSerializer(serializers.ModelSerializer):
    """
    Full person read representation.

    Computed fields:
        full_name    — "{first} {middle} {last} {suffix}" assembled from parts
        current_age  — calculated from date_of_birth and today's date;
                       null if DOB is not recorded.
                       NOTE: Use age_at_survey for historical accuracy — this
                       field shows the person's age RIGHT NOW, which increases
                       each year while age_at_survey remains frozen at survey time.
    """
    full_name    = serializers.ReadOnlyField()
    current_age  = serializers.SerializerMethodField()

    class Meta:
        model  = Person
        fields = (
            'id', 'family', 'resident',
            'role', 'full_name',
            'first_name', 'middle_name', 'last_name', 'suffix',
            'date_of_birth', 'age_at_survey', 'current_age',
            'gender', 'civil_status', 'educational_attainment',
            'is_registered_voter', 'sectors', 'data',
            'is_deleted', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'full_name', 'current_age', 'created_at', 'updated_at')

    def get_current_age(self, obj) -> int | None:
        """
        Calculate age from date_of_birth relative to today.
        Returns None if date_of_birth is not set.
        Uses the birthday method: age = years elapsed, with birthday check.
        """
        if not obj.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        dob   = obj.date_of_birth
        # Subtract 1 if birthday hasn't occurred yet this year
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
        return age


class PersonUpdateSerializer(serializers.Serializer):
    """
    Validates PATCH data for updating a Person via PersonViewSet.
    All fields are optional — only send what you want to change.
    Delegates to HouseholdService.update_person().
    """
    role                   = serializers.ChoiceField(choices=Person.Role.choices, required=False)
    first_name             = serializers.CharField(max_length=150, required=False)
    middle_name            = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name              = serializers.CharField(max_length=150, required=False)
    suffix                 = serializers.CharField(max_length=10, required=False, allow_blank=True)
    date_of_birth          = serializers.DateField(required=False, allow_null=True)
    age_at_survey          = serializers.IntegerField(min_value=0, max_value=150, required=False, allow_null=True)
    gender                 = serializers.ChoiceField(choices=Person.Gender.choices, required=False, allow_blank=True)
    civil_status           = serializers.ChoiceField(choices=Person.CivilStatus.choices, required=False, allow_blank=True)
    educational_attainment = serializers.ChoiceField(
        choices=Person.EducationalAttainment.choices, required=False, allow_blank=True
    )
    is_registered_voter    = serializers.BooleanField(required=False, allow_null=True)
    sectors                = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
    )
    data                   = serializers.DictField(required=False)


# ─────────────────────────────────────────────────────────────────────────────
# Family
# ─────────────────────────────────────────────────────────────────────────────

class FamilySerializer(serializers.ModelSerializer):
    """Full family read representation with nested persons and programs."""
    persons          = PersonSerializer(many=True, read_only=True)
    programs_availed = ProgramAvailedSerializer(many=True, read_only=True)
    person_count     = serializers.SerializerMethodField()

    class Meta:
        model  = Family
        fields = (
            'id', 'household_survey', 'family_number',
            'monthly_income_bracket', 'data',
            'persons', 'programs_availed', 'person_count',
            'is_deleted', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'family_number', 'person_count', 'created_at', 'updated_at'
        )

    def get_person_count(self, obj):
        # Use prefetched cache if available to avoid N+1
        if hasattr(obj, '_prefetched_objects_cache') and 'persons' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['persons'])
        return obj.persons.count()


class FamilyUpdateSerializer(serializers.Serializer):
    """
    Validates PATCH data for updating a Family via FamilyViewSet.
    Delegates to HouseholdService.update_family().
    """
    monthly_income_bracket = serializers.ChoiceField(
        choices=Family.IncomeBracket.choices, required=False
    )
    data = serializers.DictField(required=False)


# ─────────────────────────────────────────────────────────────────────────────
# HouseholdSurvey
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdSurveySerializer(serializers.ModelSerializer):
    """
    Full survey read representation.
    Includes nested families (with persons) for detail views.
    Use HouseholdSurveyLightSerializer for list views to avoid deep nesting.
    """
    families          = FamilySerializer(many=True, read_only=True)
    household_number  = serializers.CharField(
        source='household.household_number', read_only=True
    )
    purok             = serializers.CharField(
        source='household.purok.__str__', read_only=True
    )
    form_schema_info  = FormSchemaLightSerializer(source='form_schema', read_only=True)
    surveyed_by_name  = serializers.CharField(
        source='surveyed_by.full_name', read_only=True, default=None
    )
    verified_by_name  = serializers.CharField(
        source='verified_by.full_name', read_only=True, default=None
    )

    class Meta:
        model  = HouseholdSurvey
        fields = (
            'id', 'household', 'household_number', 'purok',
            'form_schema', 'form_schema_info',
            'survey_year', 'surveyed_by', 'surveyed_by_name',
            'surveyed_at', 'status', 'data',
            'verified_by', 'verified_by_name', 'verified_at', 'notes',
            'families',
            'is_deleted', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'household_number', 'purok', 'form_schema_info',
            'surveyed_by_name', 'verified_by_name',
            'families', 'created_at', 'updated_at',
        )


class HouseholdSurveyLightSerializer(serializers.ModelSerializer):
    """
    Compact survey representation for list views.
    No nested families — just summary counts.
    """
    household_number = serializers.CharField(
        source='household.household_number', read_only=True
    )
    purok            = serializers.CharField(
        source='household.purok.__str__', read_only=True
    )
    family_count     = serializers.SerializerMethodField()
    person_count     = serializers.SerializerMethodField()

    class Meta:
        model  = HouseholdSurvey
        fields = (
            'id', 'household', 'household_number', 'purok',
            'survey_year', 'status', 'surveyed_at',
            'family_count', 'person_count',
            'is_deleted', 'created_at', 'updated_at',
        )

    def get_family_count(self, obj):
        return obj.families.count()

    def get_person_count(self, obj):
        return Person.objects.filter(family__household_survey=obj).count()


class SurveyDataUpdateSerializer(serializers.Serializer):
    """
    Validates PATCH /surveys/{id}/ payload.
    Only the data JSON and optional metadata fields are editable post-creation.
    """
    data        = serializers.DictField(required=False)
    surveyed_at = serializers.DateField(required=False, allow_null=True)
    notes       = serializers.CharField(required=False, allow_blank=True)


# ─────────────────────────────────────────────────────────────────────────────
# CreateSurveySerializer — full nested create
# ─────────────────────────────────────────────────────────────────────────────

class _PersonInputSerializer(serializers.Serializer):
    """Validates one person entry within families_data."""
    role                   = serializers.ChoiceField(
        choices=Person.Role.choices, default=Person.Role.NON_RELATIVE
    )
    first_name             = serializers.CharField(max_length=150)
    middle_name            = serializers.CharField(max_length=150, default='', allow_blank=True)
    last_name              = serializers.CharField(max_length=150)
    suffix                 = serializers.CharField(max_length=10, default='', allow_blank=True)
    date_of_birth          = serializers.DateField(required=False, allow_null=True)
    age_at_survey          = serializers.IntegerField(min_value=0, max_value=150, required=False, allow_null=True)
    gender                 = serializers.ChoiceField(
        choices=Person.Gender.choices, default='', allow_blank=True
    )
    civil_status           = serializers.ChoiceField(
        choices=Person.CivilStatus.choices, default='', allow_blank=True
    )
    educational_attainment = serializers.ChoiceField(
        choices=Person.EducationalAttainment.choices, default='', allow_blank=True
    )
    is_registered_voter    = serializers.BooleanField(required=False, allow_null=True, default=None)
    sectors                = serializers.ListField(
        child=serializers.CharField(max_length=20),
        default=list,
    )
    data                   = serializers.DictField(default=dict)


class _ProgramInputSerializer(serializers.Serializer):
    """Validates one program entry within families_data."""
    program_type      = serializers.ChoiceField(choices=ProgramAvailed.ProgramType.choices)
    program_name      = serializers.CharField(max_length=200, default='', allow_blank=True)
    date_availed      = serializers.DateField(required=False, allow_null=True)
    amount            = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    reference_no      = serializers.CharField(max_length=100, default='', allow_blank=True)
    description       = serializers.CharField(default='', allow_blank=True)
    data              = serializers.DictField(default=dict)
    beneficiary_index = serializers.IntegerField(
        required=False, allow_null=True, min_value=0,
        help_text='0-based index into the persons array of this family. '
                  'null = whole-family benefit.'
    )


class _FamilyInputSerializer(serializers.Serializer):
    """Validates one family entry within families_data."""
    monthly_income_bracket = serializers.ChoiceField(
        choices=Family.IncomeBracket.choices,
        default=Family.IncomeBracket.UNSPECIFIED,
    )
    data     = serializers.DictField(default=dict)
    persons  = _PersonInputSerializer(many=True, min_length=1)
    programs = _ProgramInputSerializer(many=True, default=list)

    def validate(self, attrs):
        """
        Cross-validate beneficiary_index against persons list length.
        Runs after each individual field is validated.
        """
        num_persons = len(attrs.get('persons', []))
        for prog in attrs.get('programs', []):
            idx = prog.get('beneficiary_index')
            if idx is not None and idx >= num_persons:
                raise serializers.ValidationError(
                    f"beneficiary_index={idx} is out of range "
                    f"(persons list has {num_persons} entries)."
                )
        return attrs


class CreateSurveySerializer(serializers.Serializer):
    """
    Full nested create for a household survey.

    Accepts the complete survey payload in one request:
      - household_id + form_schema_id + survey metadata
      - families_data: list of families each with persons and programs

    Delegates ALL database writes to HouseholdService.create_survey()
    inside a single atomic transaction.

    Input example:
    {
      "household_id":   "uuid-...",
      "form_schema_id": "uuid-...",
      "survey_year":    2024,
      "surveyed_at":    "2024-03-15",
      "survey_data": {
        "water_source":       "metered",
        "electricity_source": "meter"
      },
      "families_data": [
        {
          "monthly_income_bracket": "5K_10K",
          "data": {"housing_tenure": "owned"},
          "persons": [
            {
              "role":       "HEAD",
              "first_name": "Juan",
              "last_name":  "Dela Cruz",
              "gender":     "MALE",
              "sectors":    ["4PS"]
            },
            {
              "role":       "SPOUSE",
              "first_name": "Maria",
              "last_name":  "Dela Cruz",
              "gender":     "FEMALE",
              "sectors":    ["LACTATING"]
            }
          ],
          "programs": [
            {
              "program_type":      "4PS",
              "program_name":      "Pantawid Pamilya",
              "date_availed":      "2024-01-15",
              "beneficiary_index": null
            }
          ]
        }
      ]
    }
    """
    household_id   = serializers.UUIDField()
    form_schema_id = serializers.UUIDField()
    survey_year    = serializers.IntegerField(min_value=2000, max_value=2100)
    surveyed_at    = serializers.DateField(required=False, allow_null=True)
    survey_data    = serializers.DictField(default=dict)
    families_data  = _FamilyInputSerializer(many=True, min_length=1)

    # Resolved objects (populated in validate_*)
    _household   = None
    _form_schema = None

    def validate_household_id(self, value):
        try:
            self._household = Household.objects.get(pk=value)
        except Household.DoesNotExist:
            raise serializers.ValidationError("Household not found.")
        return value

    def validate_form_schema_id(self, value):
        try:
            self._form_schema = FormSchema.objects.get(pk=value)
        except FormSchema.DoesNotExist:
            raise serializers.ValidationError("Form schema not found.")
        if not self._form_schema.is_active:
            raise serializers.ValidationError(
                f"Form schema '{self._form_schema.name}' is not active."
            )
        return value

    def validate(self, attrs):
        # Cross-field validation: check for duplicate survey
        year = attrs['survey_year']
        if self._household and HouseholdSurvey.objects.filter(
            household=self._household, survey_year=year
        ).exists():
            raise serializers.ValidationError(
                {
                    'survey_year': (
                        f"A survey for household "
                        f"'{self._household.household_number}' in year "
                        f"{year} already exists."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        try:
            survey = HouseholdService.create_survey(
                household=self._household,
                form_schema=self._form_schema,
                survey_year=validated_data['survey_year'],
                survey_data=validated_data.get('survey_data', {}),
                families_data=validated_data['families_data'],
                surveyed_by=request.user,
                created_by=request.user,
                surveyed_at=validated_data.get('surveyed_at'),
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except SurveyAlreadyExistsError as exc:
            # Shouldn't happen (validated above), but handle gracefully
            raise ValidationError({'survey_year': str(exc)})
        return survey


# ─────────────────────────────────────────────────────────────────────────────
# Household
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdSerializer(serializers.ModelSerializer):
    """Full household read representation."""
    purok_label       = serializers.CharField(source='purok.__str__', read_only=True)
    latest_survey_year = serializers.SerializerMethodField()
    survey_count      = serializers.SerializerMethodField()

    class Meta:
        model  = Household
        fields = (
            'id', 'household_number', 'purok', 'purok_label', 'address',
            'latitude', 'longitude', 'status', 'notes',
            'latest_survey_year', 'survey_count',
            'is_deleted', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_latest_survey_year(self, obj):
        latest = obj.surveys.order_by('-survey_year').values('survey_year').first()
        return latest['survey_year'] if latest else None

    def get_survey_count(self, obj):
        return obj.surveys.count()


class HouseholdWriteSerializer(serializers.ModelSerializer):
    """Validates POST/PATCH payload for Household."""
    class Meta:
        model   = Household
        fields  = (
            'household_number', 'purok', 'address',
            'latitude', 'longitude', 'status', 'notes',
        )

    def validate_household_number(self, value):
        # Allow blank on create (service will auto-generate)
        if not value:
            return value
        instance = self.instance
        qs = Household.objects.filter(household_number=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"Household number '{value}' is already in use."
            )
        return value


# ─────────────────────────────────────────────────────────────────────────────
# NormalizedData
# ─────────────────────────────────────────────────────────────────────────────

class NormalizedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NormalizedData
        fields = (
            'id', 'household_survey', 'survey_year',
            'level', 'source_id',
            'canonical_name', 'raw_value', 'canonical_value',
        )
        read_only_fields = fields


# ─────────────────────────────────────────────────────────────────────────────
# HouseholdChangeLog
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdChangeLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(
        source='changed_by.full_name', read_only=True, default=None
    )

    class Meta:
        model  = HouseholdChangeLog
        fields = (
            'id', 'household', 'target_type', 'target_id',
            'action', 'changed_fields',
            'changed_by', 'changed_by_name',
            'changed_at', 'ip_address', 'survey_year', 'notes',
        )
        read_only_fields = fields
