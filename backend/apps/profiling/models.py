"""
Flexible Household Profiling System — Complete Phase 1 Models
═════════════════════════════════════════════════════════════

ARCHITECTURE OVERVIEW
─────────────────────
The system separates three concerns:

  1. SCHEMA LAYER  — what questions are asked (changes yearly)
     FormSchema, FieldMapping

  2. DATA LAYER    — the actual survey responses
     Household → HouseholdSurvey → Family → Person → ProgramAvailed

  3. QUERY LAYER   — pre-flattened data for fast cross-year search
     NormalizedData

KEY INSIGHT: Household ≠ HouseholdSurvey
─────────────────────────────────────────
A Household is a PERMANENT physical record (the dwelling at 123 Rizal St.).
A HouseholdSurvey is the DATA collected in a specific year for that household.
The same household can have a 2024 survey, a 2025 survey, and a 2026 survey —
all using different form schemas. Separating these two prevents overwriting
historical data when a household is re-surveyed.

  Household (permanent)
      ├─ HouseholdSurvey 2024  ← uses FormSchema 2024 v1
      ├─ HouseholdSurvey 2025  ← uses FormSchema 2025 v1
      └─ HouseholdSurvey 2026  ← uses FormSchema 2026 v2

SOFT DELETE STRATEGY
─────────────────────
Every data model has:
  - is_deleted  (BooleanField, default=False)
  - objects     → ActiveManager  (auto-excludes deleted)
  - all_objects → AllObjectsManager  (returns everything including deleted)

Always use `Model.objects` in application code.
Use `Model.all_objects` only in admin/audit views.
"""

import uuid
from django.conf import settings
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Custom Managers  (soft delete)
# ─────────────────────────────────────────────────────────────────────────────

class ActiveManager(models.Manager):
    """
    Default manager — transparently filters out soft-deleted records.

    Any Model.objects.filter(...) call automatically adds is_deleted=False.
    Developers never need to remember to add it themselves.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """
    Unfiltered manager — returns ALL records including soft-deleted ones.

    Use this only in:
    - Admin panels (so admins can see/restore deleted records)
    - Audit views
    - Data export jobs that need complete historical data

    Usage:  Household.all_objects.filter(...)
    """
    def get_queryset(self):
        return super().get_queryset()


# ─────────────────────────────────────────────────────────────────────────────
# Soft Delete Mixin
# ─────────────────────────────────────────────────────────────────────────────

class SoftDeleteMixin(models.Model):
    """
    Abstract mixin that adds soft-delete fields and methods to any model.

    Include this in every data model. Do NOT use Django's built-in delete()
    directly — always call .soft_delete(user) instead.

    TRADE-OFF: Every query through `objects` automatically gets
    `WHERE is_deleted = FALSE` appended. This is nearly free with a proper
    index but means raw SQL or all_objects must be used for full data access.
    """
    is_deleted  = models.BooleanField(default=False, db_index=True)
    deleted_at  = models.DateTimeField(null=True, blank=True)
    deleted_by  = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='%(class)s_deletions')

    objects     = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self, deleted_by_user=None):
        """Mark as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by_user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """Undo a soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


# ─────────────────────────────────────────────────────────────────────────────
# Audit Mixin
# ─────────────────────────────────────────────────────────────────────────────

class AuditMixin(models.Model):
    """
    Abstract mixin that adds who-created/who-updated tracking.
    Combined with SoftDeleteMixin on every data model.
    """
    created_by  = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='%(class)s_created')
    updated_by  = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='%(class)s_updated')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA LAYER
# ─────────────────────────────────────────────────────────────────────────────

class FormSchema(models.Model):
    """
    Stores one version of the household survey form for a given year.

    WHY in the database (not hardcoded):
        The barangay revises its form every year based on national government
        requirements (DILG, DSWD, PSA). Hardcoding the form means every
        change requires a developer + deployment. Storing it here means an
        admin can update the form in minutes without touching code.

    VERSIONING:
        A year can have multiple versions (v1, v2) if the form is revised
        mid-year. Only one version per year should be is_active=True for
        new data entry. Old versions remain readable for historical data.

    SCHEMA JSON STRUCTURE:
    ─────────────────────
    {
      "sections": [
        {
          "id": "household_facilities",
          "label": "Household Facilities",
          "level": "household",         ← which model this section fills
          "fields": [
            {
              "id": "water_source",     ← key used in HouseholdSurvey.data
              "canonical": "water_source",  ← maps to FieldMapping
              "label": "Water Source",
              "type": "select",         ← text|number|select|multiselect|date|boolean|textarea
              "options": [
                {"value": "nature",  "label": "Nature/Spring"},
                {"value": "poso",    "label": "Poso / Deep Well"},
                {"value": "metered", "label": "Metered / Level 3"}
              ],
              "required": true,
              "help_text": "Primary source of drinking water"
            },
            {
              "id": "electricity_source",
              "canonical": "electricity_source",
              "label": "Electricity Source",
              "type": "select",
              "options": [
                {"value": "none",  "label": "None"},
                {"value": "solar", "label": "Solar"},
                {"value": "meter", "label": "Metered (POCO/BLCI)"},
                {"value": "tap",   "label": "Tap (shared meter)"}
              ],
              "required": true,
              "help_text": ""
            }
          ]
        },
        {
          "id": "family_info",
          "label": "Family Information",
          "level": "family",
          "fields": [ ... ]
        },
        {
          "id": "person_info",
          "label": "Person Information",
          "level": "person",
          "fields": [ ... ]
        }
      ]
    }

    TRADE-OFFS:
        + No code deployment needed for form changes
        + Historical data always paired with correct form definition
        - Frontend must render forms dynamically (more complex)
        - Schema validation must happen in Python/JS, not DB constraints
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year        = models.PositiveSmallIntegerField(
                    db_index=True,
                    help_text='Survey year, e.g. 2024')
    version     = models.PositiveSmallIntegerField(
                    default=1,
                    help_text='Increments if form is revised within the same year (2024 v1, 2024 v2)')
    name        = models.CharField(
                    max_length=200,
                    help_text='Human-readable label, e.g. "Barangay Household Survey 2024 v1"')
    description = models.TextField(blank=True)
    schema      = models.JSONField(
                    help_text='Full form definition — see class docstring for structure')
    is_active   = models.BooleanField(
                    default=True,
                    db_index=True,
                    help_text='Only one schema per year should be active for new data entry')
    created_by  = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='created_schemas')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Form Schema'
        verbose_name_plural = 'Form Schemas'
        ordering            = ['-year', '-version']
        unique_together     = ('year', 'version')
        indexes             = [
            models.Index(fields=['year', 'is_active']),
        ]

    def __str__(self):
        status = 'ACTIVE' if self.is_active else 'archived'
        return f'{self.name} [{status}]'

    def get_fields_for_level(self, level: str) -> list:
        """
        Return all field definitions for a given level.
        level: 'household' | 'family' | 'person'
        """
        fields = []
        for section in self.schema.get('sections', []):
            if section.get('level') == level:
                fields.extend(section.get('fields', []))
        return fields

    def get_canonical_map(self) -> dict:
        """
        Returns {field_id: canonical_name} for all fields in this schema.
        Used by the normalization job to populate NormalizedData.
        """
        result = {}
        for section in self.schema.get('sections', []):
            for field in section.get('fields', []):
                result[field['id']] = field.get('canonical', field['id'])
        return result


class FieldMapping(models.Model):
    """
    Cross-year translation layer for querying the same concept across
    different survey years with different field names.

    PROBLEM IT SOLVES:
        In 2024: household.data['water_source'] = 'metered'
        In 2026: household.data['water_access_level'] = 'level_3'
        Query: "Find all households with metered/level_3 water (2024–2026)"
        → Without this model, you need custom code per year combination.
        → With this model, a generic query service handles it automatically.

    YEAR MAP JSON STRUCTURE:
    ────────────────────────
    {
      "2024": {
        "field_name": "water_source",
        "value_map": {
          "nature":  "level_1",
          "poso":    "level_2",
          "metered": "level_3"
        }
      },
      "2025": {
        "field_name": "water_source",
        "value_map": {
          "nature":  "level_1",
          "poso":    "level_2",
          "metered": "level_3"
        }
      },
      "2026": {
        "field_name": "water_access_level",
        "value_map": {
          "level_1": "level_1",
          "level_2": "level_2",
          "level_3": "level_3"
        }
      }
    }

    HOW A CROSS-YEAR QUERY WORKS:
        1. User selects canonical_name="water_source", value="level_3", years=[2024,2025,2026]
        2. Query service looks up year_map for each year
        3. For 2024: field_name="water_source", look for value_map key where value="level_3" → "metered"
        4. For 2026: field_name="water_access_level", value="level_3"
        5. SQL: WHERE (year=2024 AND data->>'water_source'='metered')
                   OR (year=2026 AND data->>'water_access_level'='level_3')

    TRADE-OFFS:
        + Cross-year queries work without custom code
        + Old reports stay valid even when terminology changes
        - Someone must MAINTAIN this table whenever a new form is released
        - Missing a mapping means silently incomplete cross-year results
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_name = models.CharField(
                       max_length=100, unique=True,
                       help_text='Stable internal identifier that never changes, e.g. "water_source"')
    label          = models.CharField(
                       max_length=200,
                       help_text='Display label used in reports, e.g. "Water Source"')
    level          = models.CharField(
                       max_length=10,
                       choices=[('household','Household'),('family','Family'),('person','Person')],
                       help_text='Which model level this field belongs to')
    data_type      = models.CharField(
                       max_length=15,
                       choices=[
                           ('text','Text'),('number','Number'),
                           ('select','Select'),('multiselect','Multi-select'),
                           ('boolean','Yes/No'),('date','Date'),
                       ],
                       default='select')
    canonical_options = models.JSONField(
                       default=list,
                       help_text='Stable list of all possible values across all years. '
                                 'Example: [{"value":"level_1","label":"Nature/Spring"}, ...]')
    year_map       = models.JSONField(
                       default=dict,
                       help_text='Maps year → {field_name, value_map} — see class docstring')
    notes          = models.TextField(blank=True,
                       help_text='Document why mappings changed between years')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Field Mapping'
        verbose_name_plural = 'Field Mappings'
        ordering            = ['level', 'canonical_name']

    def __str__(self):
        return f'{self.label} ({self.canonical_name}) [{self.level}]'

    def get_query_args(self, canonical_value: str, year: int) -> dict | None:
        """
        Returns the actual JSON field name and value to use in a DB query
        for a specific year.

        Example:
            mapping.get_query_args('level_3', 2024)
            → {'field': 'water_source', 'value': 'metered'}

        Returns None if this year has no mapping defined.
        """
        entry = self.year_map.get(str(year))
        if not entry:
            return None
        value_map_inverted = {v: k for k, v in entry.get('value_map', {}).items()}
        actual_value = value_map_inverted.get(canonical_value, canonical_value)
        return {'field': entry['field_name'], 'value': actual_value}

    def get_canonical_value(self, year: int, raw_value: str) -> str | None:
        """
        Translates a raw value from a specific year into its canonical value.

        Example:
            mapping.get_canonical_value(2024, 'metered') → 'level_3'
            mapping.get_canonical_value(2026, 'level_3') → 'level_3'
        """
        entry = self.year_map.get(str(year))
        if not entry:
            return raw_value
        return entry.get('value_map', {}).get(raw_value, raw_value)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LAYER
# ─────────────────────────────────────────────────────────────────────────────

class Household(SoftDeleteMixin, AuditMixin):
    """
    Permanent record of a physical dwelling unit.

    WHY separate from HouseholdSurvey:
        A Household is a permanent entity — the building at 123 Rizal St. in
        Purok 3. It exists independently of any survey.
        A HouseholdSurvey is the data collected about that household in a
        specific year. Separating them means:
        - One household can have survey data for 2024, 2025, and 2026
        - Re-surveying in 2026 DOESN'T overwrite 2024/2025 data
        - Historical comparison is built-in (not reconstructed from logs)

    FIXED FIELDS (always queryable via ORM/SQL without JSON extraction):
        household_number — barangay-assigned code, used in official records
        purok            — physical location, used in every filter
        address          — full street address
        status           — whether household is currently occupied/active

    NO JSON DATA HERE:
        The Household model itself has no JSON data field. All survey
        responses are in HouseholdSurvey.data. This keeps the Household
        record clean and stable.
    """
    class Status(models.TextChoices):
        ACTIVE    = 'ACTIVE',    'Active / Occupied'
        VACANT    = 'VACANT',    'Vacant'
        ABANDONED = 'ABANDONED', 'Abandoned'
        DEMOLISHED = 'DEMOLISHED', 'Demolished'

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household_number = models.CharField(
                         max_length=30, unique=True,
                         help_text='Barangay-assigned code, e.g. "PRK3-2024-001". Never changes.')
    purok            = models.ForeignKey(
                         'residents.Purok', on_delete=models.PROTECT,
                         related_name='households')
    address          = models.TextField(
                         blank=True,
                         help_text='Full street address within the purok')
    latitude         = models.DecimalField(
                         max_digits=9, decimal_places=6,
                         null=True, blank=True,
                         help_text='GPS latitude for map display')
    longitude        = models.DecimalField(
                         max_digits=9, decimal_places=6,
                         null=True, blank=True,
                         help_text='GPS longitude for map display')
    status           = models.CharField(
                         max_length=12, choices=Status.choices,
                         default=Status.ACTIVE, db_index=True)
    notes            = models.TextField(blank=True)

    class Meta:
        verbose_name        = 'Household'
        verbose_name_plural = 'Households'
        ordering            = ['purok', 'household_number']
        indexes             = [
            models.Index(fields=['purok', 'status']),
            models.Index(fields=['is_deleted', 'status']),
        ]

    def __str__(self):
        return f'Household {self.household_number} ({self.purok})'

    @property
    def latest_survey(self):
        return self.surveys.order_by('-survey_year').first()


class HouseholdSurvey(SoftDeleteMixin, AuditMixin):
    """
    One survey response for a household in a specific year.

    This is where the flexible JSON data lives.

    WHY separate from Household:
        See Household docstring. The key benefit: if barangay staff re-surveys
        a household in 2026, they create a NEW HouseholdSurvey for 2026.
        The 2024 and 2025 surveys remain completely intact and readable.

    WHAT GOES IN data JSON:
    ────────────────────────
    The `data` field stores answers to ALL household-level questions from the
    FormSchema. The keys are the field `id` values from the schema sections
    where level="household".

    Example for a 2024 survey:
    {
      "water_source": "metered",
      "electricity_source": "meter",
      "toilet_type": "flush",
      "house_type": "concrete",
      "roof_material": "gi_sheet",
      "floor_material": "concrete",
      "num_rooms": 3,
      "has_kitchen": true,
      "waste_disposal": "collected"
    }

    Example for the same household in a 2026 survey (different field names!):
    {
      "water_access_level": "level_3",
      "electricity_source": "meter",
      "sanitation_facility": "water_sealed",
      "house_structure": "permanent",
      "roof_material": "gi_sheet",
      "num_rooms": 3,
      "has_kitchen": true,
      "solid_waste_management": "door_to_door"
    }

    VERSIONING:
        form_schema  FK tells you which form was used → what's in data
        survey_year  denormalized for fast filtering without JOIN

    STATUS FLOW:
        DRAFT → data is being entered, not yet complete
        SUBMITTED → staff submitted, pending verification
        VERIFIED → supervisor reviewed and approved
        REVISION → sent back for corrections

    INDEXES:
        GIN index on `data` allows PostgreSQL to search inside JSON:
        SELECT * FROM household_survey WHERE data->>'water_source' = 'metered'
        This is ~100x faster than a full table scan.
    """
    class SurveyStatus(models.TextChoices):
        DRAFT     = 'DRAFT',     'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        VERIFIED  = 'VERIFIED',  'Verified'
        REVISION  = 'REVISION',  'Needs Revision'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household   = models.ForeignKey(
                    Household, on_delete=models.CASCADE,
                    related_name='surveys',
                    help_text='The physical household this survey is about')
    form_schema = models.ForeignKey(
                    FormSchema, on_delete=models.PROTECT,
                    related_name='surveys',
                    help_text='Which form version was used — determines what is in data JSON')
    survey_year = models.PositiveSmallIntegerField(
                    db_index=True,
                    help_text='Denormalized year for fast filtering without JOIN to FormSchema')
    surveyed_by = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='conducted_surveys',
                    help_text='Staff member who collected this data')
    surveyed_at = models.DateField(
                    null=True, blank=True,
                    help_text='Date the survey was physically conducted')
    status      = models.CharField(
                    max_length=10,
                    choices=SurveyStatus.choices,
                    default=SurveyStatus.DRAFT,
                    db_index=True)

    # All dynamic household-level answers from the form
    data        = models.JSONField(
                    default=dict,
                    help_text='Answers to household-level form fields. Keys match FormSchema field IDs.')

    verified_by = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='verified_surveys')
    verified_at = models.DateTimeField(null=True, blank=True)
    notes       = models.TextField(blank=True, help_text='Supervisor notes during verification')

    class Meta:
        verbose_name        = 'Household Survey'
        verbose_name_plural = 'Household Surveys'
        ordering            = ['-survey_year', 'household']
        # One survey per household per year (prevent duplicate entries)
        unique_together     = ('household', 'survey_year')
        indexes             = [
            models.Index(fields=['survey_year', 'status']),
            models.Index(fields=['household', 'survey_year']),
            models.Index(fields=['is_deleted', 'survey_year']),
            # PostgreSQL GIN index — enables fast JSON field queries
            GinIndex(fields=['data'], name='household_survey_data_gin'),
        ]

    def __str__(self):
        return f'{self.household} — Survey {self.survey_year}'


class Family(SoftDeleteMixin, AuditMixin):
    """
    A nuclear family unit within a household survey.

    WHY multiple families per survey:
        Filipino households frequently have multiple nuclear families sharing
        one address — e.g., grandparents + two married children with their
        own families. Each family has its own income, programs, and head.
        Without this model, this structure cannot be represented accurately.

    family_number is sequential within the household_survey (1, 2, 3...).
    It is set at creation and NEVER changes, even if earlier families
    are soft-deleted. This gives staff a stable reference number.

    INCOME BRACKET:
        Stored as an enum choice, not in the JSON data, because:
        - Income bracket is used in almost every household report
        - It needs to be filterable and sortable efficiently
        - It's a universally stable concept that doesn't change year to year

    WHAT GOES IN data JSON:
    ────────────────────────
    Dynamic family-level questions from the schema (level="family"):
    {
      "housing_tenure": "owned",
      "years_in_area": 12,
      "has_farm": false,
      "farm_area_sqm": null
    }
    """
    class IncomeBracket(models.TextChoices):
        NO_INCOME   = 'NO_INCOME',   'No Income'
        BELOW_5K    = 'BELOW_5K',    'Below ₱5,000'
        INC_5K_10K  = '5K_10K',      '₱5,000 – ₱9,999'
        INC_10K_20K = '10K_20K',     '₱10,000 – ₱19,999'
        INC_20K_30K = '20K_30K',     '₱20,000 – ₱29,999'
        INC_30K_50K = '30K_50K',     '₱30,000 – ₱49,999'
        ABOVE_50K   = 'ABOVE_50K',   '₱50,000 and above'
        UNSPECIFIED = 'UNSPECIFIED', 'Not Specified'

    id                     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household_survey       = models.ForeignKey(
                               HouseholdSurvey, on_delete=models.CASCADE,
                               related_name='families')
    family_number          = models.PositiveSmallIntegerField(
                               help_text='Sequential within this survey (1, 2, 3...). Never changes.')
    monthly_income_bracket = models.CharField(
                               max_length=12,
                               choices=IncomeBracket.choices,
                               default=IncomeBracket.UNSPECIFIED,
                               db_index=True)
    data                   = models.JSONField(
                               default=dict,
                               help_text='Answers to family-level form fields')

    class Meta:
        verbose_name        = 'Family'
        verbose_name_plural = 'Families'
        ordering            = ['household_survey', 'family_number']
        unique_together     = ('household_survey', 'family_number')
        indexes             = [
            models.Index(fields=['household_survey', 'is_deleted']),
            models.Index(fields=['monthly_income_bracket', 'is_deleted']),
        ]

    def __str__(self):
        return f'Family {self.family_number} of {self.household_survey}'


class Person(SoftDeleteMixin, AuditMixin):
    """
    An individual member of a family.

    FIXED vs JSON — the decision rule:
        A field is FIXED (dedicated column) if ALL of these are true:
          1. It appears in EVERY year's form without renaming
          2. It needs to be filterable/sortable directly
          3. It has a stable, predictable set of values

        Everything else goes in `data` JSON.

    FIXED columns (always queryable):
        first_name, middle_name, last_name, suffix — used in search everywhere
        date_of_birth — used for age-range queries
        gender — used in demographic reports
        civil_status — used in social welfare analysis
        educational_attainment — used in literacy/education reports
        is_registered_voter — used in voter registration reports
        role — determines who is head of family
        sectors — JSON array for multi-value sector membership

    WHY `sectors` is a JSON array (not a many-to-many):
        A person can belong to 5 sectors simultaneously (PWD + Solo Parent +
        4Ps + Senior + IP). A many-to-many join table would require a JOIN
        for every person query. A JSON array with a GIN index lets you query
        "find all PWD persons" with a single JSON containment operator (@>).

        PostgreSQL:  WHERE sectors @> '["PWD"]'
        Django ORM:  Person.objects.filter(sectors__contains=['PWD'])

    WHAT GOES IN data JSON:
    ────────────────────────
    Dynamic person-level questions from the schema (level="person"):
    {
      "religion": "Roman Catholic",
      "occupation": "Farmer",
      "employer": "Self-employed",
      "monthly_income": 8000,
      "voter_precinct": "PRK3-001",
      "philhealth_no": "12-345678901-2",
      "sss_no": "",
      "has_disability_id": true,
      "disability_type": "Physical"
    }
    """
    class Role(models.TextChoices):
        HEAD        = 'HEAD',        'Head of Family'
        SPOUSE      = 'SPOUSE',      'Spouse / Partner'
        CHILD       = 'CHILD',       'Child'
        PARENT      = 'PARENT',      'Parent of Head'
        SIBLING     = 'SIBLING',     'Sibling'
        RELATIVE    = 'RELATIVE',    'Other Relative'
        NON_RELATIVE = 'NON_RELATIVE', 'Non-Relative'

    class Gender(models.TextChoices):
        MALE   = 'MALE',   'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER  = 'OTHER',  'Other / Prefer not to say'

    class CivilStatus(models.TextChoices):
        SINGLE    = 'SINGLE',    'Single'
        MARRIED   = 'MARRIED',   'Married'
        WIDOWED   = 'WIDOWED',   'Widowed'
        SEPARATED = 'SEPARATED', 'Separated'
        ANNULLED  = 'ANNULLED',  'Annulled'
        LIVE_IN   = 'LIVE_IN',   'Live-in'

    class EducationalAttainment(models.TextChoices):
        NO_FORMAL    = 'NO_FORMAL',    'No Formal Education'
        KINDER       = 'KINDER',       'Kinder'
        ELEM         = 'ELEM',         'Elementary (Ongoing)'
        ELEM_GRAD    = 'ELEM_GRAD',    'Elementary Graduate'
        JHS          = 'JHS',          'Junior High School (Ongoing)'
        JHS_GRAD     = 'JHS_GRAD',     'Junior High School Graduate'
        SHS          = 'SHS',          'Senior High School (Ongoing)'
        SHS_GRAD     = 'SHS_GRAD',     'Senior High School Graduate'
        VOCATIONAL   = 'VOCATIONAL',   'Vocational / TESDA'
        COLLEGE      = 'COLLEGE',      'College (Ongoing)'
        COLLEGE_GRAD = 'COLLEGE_GRAD', 'College Graduate'
        POST_GRAD    = 'POST_GRAD',    'Post-Graduate'

    SECTOR_CHOICES = [
        ('PWD',         'Person with Disability (PWD)'),
        ('SOLO_PARENT', 'Solo Parent'),
        ('4PS',         '4Ps / Pantawid Pamilya Beneficiary'),
        ('IP',          'Indigenous People (IP)'),
        ('SENIOR',      'Senior Citizen (60+)'),
        ('YOUTH',       'Youth (15–30)'),
        ('LACTATING',   'Lactating / Pregnant Mother'),
        ('OFW',         'Overseas Filipino Worker (OFW) Family'),
    ]

    id                     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family                 = models.ForeignKey(
                               Family, on_delete=models.CASCADE,
                               related_name='persons')
    resident               = models.ForeignKey(
                               'residents.Resident', on_delete=models.SET_NULL,
                               null=True, blank=True,
                               related_name='profiling_entries',
                               help_text='Links to portal Resident record if one exists')

    # ── Fixed personal fields ──
    role                   = models.CharField(max_length=15, choices=Role.choices,
                               default=Role.NON_RELATIVE, db_index=True)
    first_name             = models.CharField(max_length=150)
    middle_name            = models.CharField(max_length=150, blank=True)
    last_name              = models.CharField(max_length=150)
    suffix                 = models.CharField(max_length=10, blank=True,
                               help_text='Jr., Sr., III, etc.')
    date_of_birth          = models.DateField(null=True, blank=True, db_index=True)
    age_at_survey          = models.PositiveSmallIntegerField(
                               null=True, blank=True,
                               help_text='Age recorded at time of survey — preserved even as DOB ages')
    gender                 = models.CharField(max_length=10, choices=Gender.choices,
                               blank=True, db_index=True)
    civil_status           = models.CharField(max_length=10, choices=CivilStatus.choices,
                               blank=True, db_index=True)
    educational_attainment = models.CharField(max_length=15,
                               choices=EducationalAttainment.choices,
                               blank=True, db_index=True)
    is_registered_voter    = models.BooleanField(null=True, blank=True)

    # Sector membership — JSON array for multiple simultaneous values
    sectors                = models.JSONField(
                               default=list,
                               help_text='List of sector codes. '
                                         'Example: ["PWD", "SOLO_PARENT"]. '
                                         'Query: Person.objects.filter(sectors__contains=["PWD"])')

    # Dynamic person-level answers from the form
    data                   = models.JSONField(
                               default=dict,
                               help_text='Answers to person-level form fields')

    class Meta:
        verbose_name        = 'Person'
        verbose_name_plural = 'Persons'
        ordering            = ['family', 'role', 'last_name', 'first_name']
        indexes             = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['family', 'role']),
            models.Index(fields=['gender', 'is_deleted']),
            models.Index(fields=['educational_attainment', 'is_deleted']),
            models.Index(fields=['date_of_birth']),
            # GIN index — fast JSON containment queries on sectors
            # Query: Person.objects.filter(sectors__contains=['PWD'])
            GinIndex(fields=['sectors'], name='person_sectors_gin'),
            GinIndex(fields=['data'],    name='person_data_gin'),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        name = ' '.join(filter(None, parts))
        return f'{name} {self.suffix}'.strip() if self.suffix else name


class ProgramAvailed(SoftDeleteMixin, AuditMixin):
    """
    A specific government or barangay assistance program availed by a family.

    WHY a separate table (not in Family.data JSON):
        Programs have their own rich structure (date, amount, reference number)
        and a family can avail MULTIPLE programs. Putting them in JSON makes
        querying ("find all families with 4Ps") slow and awkward.
        A proper table with indexes makes this trivial.

    TRADE-OFF: More tables to JOIN in reports, but filtering by program type
    is fast and correct.

    `beneficiary` points to the specific Person who is the named beneficiary
    (important for scholarships, PWD assistance, solo parent aid, etc.).
    It's nullable because some programs (relief goods) apply to the whole family.
    """
    class ProgramType(models.TextChoices):
        FINANCIAL   = 'FINANCIAL',   'Financial Assistance'
        EDUCATIONAL = 'EDUCATIONAL', 'Educational Assistance / Scholarship'
        MEDICAL     = 'MEDICAL',     'Medical Assistance'
        LIVELIHOOD  = 'LIVELIHOOD',  'Livelihood / Skills Training'
        FOUR_PS     = '4PS',         '4Ps / Pantawid Pamilya'
        NATIONAL    = 'NATIONAL',    'National Government (DSWD / DOLE / DAR)'
        RELIEF      = 'RELIEF',      'Relief Goods / Emergency Aid'
        HOUSING     = 'HOUSING',     'Housing Assistance'
        OTHER       = 'OTHER',       'Other'

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family        = models.ForeignKey(
                      Family, on_delete=models.CASCADE,
                      related_name='programs_availed')
    beneficiary   = models.ForeignKey(
                      Person, on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name='programs_availed',
                      help_text='Named beneficiary, if program is for one person rather than whole family')
    program_type  = models.CharField(max_length=12, choices=ProgramType.choices,
                      db_index=True)
    program_name  = models.CharField(max_length=200, blank=True,
                      help_text='Specific program name, e.g. "AICS", "TUPAD", "DSWD SLP"')
    date_availed  = models.DateField(null=True, blank=True, db_index=True)
    amount        = models.DecimalField(max_digits=12, decimal_places=2,
                      null=True, blank=True)
    reference_no  = models.CharField(max_length=100, blank=True,
                      help_text='Government control or reference number')
    description   = models.TextField(blank=True)
    data          = models.JSONField(default=dict,
                      help_text='Any extra structured fields for this program')

    class Meta:
        verbose_name        = 'Program Availed'
        verbose_name_plural = 'Programs Availed'
        ordering            = ['-date_availed', 'program_type']
        indexes             = [
            models.Index(fields=['program_type', 'date_availed']),
            models.Index(fields=['family', 'program_type']),
            models.Index(fields=['is_deleted', 'program_type']),
        ]

    def __str__(self):
        return f'{self.get_program_type_display()} — Family {self.family.family_number}'


# ─────────────────────────────────────────────────────────────────────────────
# QUERY LAYER  (pre-flattened for fast cross-year search)
# ─────────────────────────────────────────────────────────────────────────────

class NormalizedData(models.Model):
    """
    Pre-flattened lookup table for fast cross-year JSON field queries.

    PROBLEM:
        Cross-year queries on JSON fields require complex SQL:
          (year=2024 AND data->>'water_source'='metered')
          OR (year=2026 AND data->>'water_access_level'='level_3')
        This gets unwieldy with many fields and many years.

    SOLUTION:
        After each HouseholdSurvey is saved, a background job (Django signal
        or Celery task) reads the data JSON and writes one NormalizedData row
        per field, translating raw values to canonical values using FieldMapping.

        The result for the water source example:
        ┌──────────────┬───────────────┬───────────────┬──────────────┐
        │ survey_year  │ canonical_name│ raw_value     │ canonical_val│
        ├──────────────┼───────────────┼───────────────┼──────────────┤
        │ 2024         │ water_source  │ metered       │ level_3      │
        │ 2026         │ water_source  │ level_3       │ level_3      │
        └──────────────┴───────────────┴───────────────┴──────────────┘

        Cross-year query becomes:
          NormalizedData.objects.filter(
              canonical_name='water_source',
              canonical_value='level_3',
              survey_year__range=(2024, 2026)
          ).values_list('household_survey_id', flat=True)

    THIS IS A READ-ONLY TABLE:
        Never write to it directly. It is always regenerated from
        HouseholdSurvey.data + FieldMapping. If data changes, the
        normalization job runs again and replaces existing rows.

    TRADE-OFFS:
        + Cross-year queries become trivial O(1) lookups
        + Report builder can query without knowing field name per year
        - Storage doubles (data is in both HouseholdSurvey.data and here)
        - Must be kept in sync — a background job failure leaves it stale
        - Only covers fields that have a FieldMapping (unmapped fields not here)
    """
    id               = models.BigAutoField(primary_key=True)
    household_survey = models.ForeignKey(
                         HouseholdSurvey, on_delete=models.CASCADE,
                         related_name='normalized_data',
                         db_index=True)
    survey_year      = models.PositiveSmallIntegerField(db_index=True)
    level            = models.CharField(
                         max_length=10,
                         choices=[('household','Household'),('family','Family'),('person','Person')])
    # Which specific record this row came from (Family.id or Person.id)
    source_id        = models.UUIDField(
                         null=True, blank=True, db_index=True,
                         help_text='UUID of the Family or Person this value came from. '
                                   'NULL for household-level fields.')
    canonical_name   = models.CharField(
                         max_length=100, db_index=True,
                         help_text='FieldMapping.canonical_name')
    raw_value        = models.CharField(
                         max_length=500,
                         help_text='Original value from the data JSON, exactly as stored')
    canonical_value  = models.CharField(
                         max_length=500,
                         help_text='Value translated to the canonical vocabulary via FieldMapping')

    class Meta:
        verbose_name        = 'Normalized Data'
        verbose_name_plural = 'Normalized Data'
        indexes             = [
            # The primary query pattern: find surveys with canonical_name=X, value=Y, year in range
            models.Index(fields=['canonical_name', 'canonical_value', 'survey_year'],
                         name='norm_canonical_year_idx'),
            models.Index(fields=['household_survey', 'canonical_name'],
                         name='norm_survey_canonical_idx'),
            models.Index(fields=['survey_year', 'level'],
                         name='norm_year_level_idx'),
        ]

    def __str__(self):
        return f'{self.canonical_name}={self.canonical_value} (Survey {self.survey_year})'


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT TRAIL
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdChangeLog(models.Model):
    """
    Field-level audit trail for all changes to profiling data.

    WHY separate from the system AuditLog:
        The system AuditLog records security events:
          "Admin X deleted Household Y at 10:32am"
        This model records DATA events:
          "Field water_source changed from 'poso' to 'metered' on March 15
           by Staff Maria Santos, survey 2024, household PRK3-2024-001"

        You need both. The system log is for security auditing.
        This log is for data quality and compliance auditing.

    HOW TO USE:
        Call HouseholdChangeLog.log_change() from the service layer
        whenever a survey, family, or person record is created/updated/deleted.
        Do NOT put this logic in model.save() — it belongs in the service layer
        where you have access to request.user.

    CHANGED_FIELDS JSON STRUCTURE:
    ───────────────────────────────
    {
      "water_source": {
        "old": "poso",
        "new": "metered"
      },
      "num_rooms": {
        "old": 2,
        "new": 3
      }
    }

    For JSON field changes, the entire JSON is stored as old/new.
    For soft deletes, changed_fields = {"is_deleted": {"old": false, "new": true}}.
    """
    class TargetType(models.TextChoices):
        SURVEY  = 'SURVEY',  'Household Survey'
        FAMILY  = 'FAMILY',  'Family'
        PERSON  = 'PERSON',  'Person'
        PROGRAM = 'PROGRAM', 'Program Availed'

    class Action(models.TextChoices):
        CREATED  = 'CREATED',  'Created'
        UPDATED  = 'UPDATED',  'Updated'
        DELETED  = 'DELETED',  'Soft Deleted'
        RESTORED = 'RESTORED', 'Restored'
        VERIFIED = 'VERIFIED', 'Verified'
        REVISION = 'REVISION', 'Sent for Revision'

    id             = models.BigAutoField(primary_key=True)
    # Which household does this change belong to (for quick household history)
    household      = models.ForeignKey(
                       Household, on_delete=models.CASCADE,
                       related_name='change_logs')
    target_type    = models.CharField(max_length=8, choices=TargetType.choices,
                       db_index=True)
    target_id      = models.UUIDField(db_index=True,
                       help_text='UUID of the specific record that was changed')
    action         = models.CharField(max_length=10, choices=Action.choices)
    changed_fields = models.JSONField(
                       default=dict,
                       help_text='{"field_name": {"old": "...", "new": "..."}}')
    changed_by     = models.ForeignKey(
                       settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                       null=True, blank=True, related_name='profiling_changes')
    changed_at     = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address     = models.GenericIPAddressField(null=True, blank=True)
    survey_year    = models.PositiveSmallIntegerField(
                       null=True, blank=True, db_index=True,
                       help_text='Denormalized for filtering change history by year')
    notes          = models.TextField(blank=True)

    class Meta:
        verbose_name        = 'Household Change Log'
        verbose_name_plural = 'Household Change Logs'
        ordering            = ['-changed_at']
        indexes             = [
            models.Index(fields=['household', 'changed_at']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['changed_by', 'changed_at']),
        ]

    def __str__(self):
        return f'{self.action} {self.target_type} by {self.changed_by} at {self.changed_at}'

    @classmethod
    def log_change(cls, household, target_type, target_id, action,
                   changed_fields, changed_by, ip_address=None,
                   survey_year=None, notes=''):
        """
        Factory method for creating log entries cleanly from service layer.

        Usage in services.py:
            HouseholdChangeLog.log_change(
                household=survey.household,
                target_type=HouseholdChangeLog.TargetType.SURVEY,
                target_id=survey.id,
                action=HouseholdChangeLog.Action.UPDATED,
                changed_fields={
                    'water_source': {'old': 'poso', 'new': 'metered'}
                },
                changed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                survey_year=survey.survey_year,
            )
        """
        return cls.objects.create(
            household=household,
            target_type=target_type,
            target_id=target_id,
            action=action,
            changed_fields=changed_fields,
            changed_by=changed_by,
            ip_address=ip_address,
            survey_year=survey_year,
            notes=notes,
        )
