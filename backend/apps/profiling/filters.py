"""
Profiling App — Filter Classes (Phase 3)
══════════════════════════════════════════════════════════════════════════════

Django-filter FilterSet definitions for each model.
Consumed by ViewSets via `filterset_class = XxxFilter`.

FILTER DESIGN PRINCIPLES
─────────────────────────
  • Exact matches use the model's choice sets (ChoiceFilter) so invalid
    values are rejected at the filter level, not silently ignored.
  • Range params use _min / _max suffixes (year_min, year_max, age_min...).
  • Multi-value list params use BaseInFilter (years=2024,2025,2026).
  • JSON-field queries (sector containment, data key lookups) use custom
    filter methods — the underlying SQL uses @> (GIN index path).
  • Age filtering prefers `age_at_survey` (snapshot value) over
    date_of_birth arithmetic to keep results historically accurate.

USAGE
─────
  GET /households/?purok=3&status=ACTIVE
  GET /surveys/?year_min=2022&year_max=2024&status=VERIFIED
  GET /surveys/?years=2022,2023,2024&purok=3
  GET /persons/?gender=FEMALE&sector=PWD&age_min=18&age_max=59
  GET /persons/?educational_attainment=COLLEGE_GRAD&survey_year=2024
  GET /programs/?program_type=4PS&date_from=2024-01-01&date_to=2024-12-31
"""

from datetime import date

import django_filters
from django.db.models import Q

from .models import Family, Household, HouseholdSurvey, Person, ProgramAvailed


# ─────────────────────────────────────────────────────────────────────────────
# HouseholdFilter
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdFilter(django_filters.FilterSet):
    """
    Filter Household records by location and status.

    Params:
        purok           — filter by Purok.number (e.g. purok=3)
        purok_id        — filter by Purok PK (UUID)
        status          — ACTIVE | VACANT | ABANDONED | DEMOLISHED
        surveyed_year   — has at least one survey in this year
        has_surveys     — true/false: has any surveys at all
    """
    purok         = django_filters.NumberFilter(
        field_name='purok__number',
        label='Purok number',
    )
    purok_id      = django_filters.UUIDFilter(
        field_name='purok',
        label='Purok UUID',
    )
    status        = django_filters.ChoiceFilter(choices=Household.Status.choices)
    surveyed_year = django_filters.NumberFilter(
        method='filter_surveyed_year',
        label='Has survey in year',
    )
    has_surveys   = django_filters.BooleanFilter(
        method='filter_has_surveys',
        label='Has any survey record',
    )

    class Meta:
        model  = Household
        fields = ['status']

    def filter_surveyed_year(self, qs, name, value):
        return qs.filter(
            surveys__survey_year=value,
            surveys__is_deleted=False,
        ).distinct()

    def filter_has_surveys(self, qs, name, value):
        method = 'exclude' if not value else 'filter'
        return getattr(qs, method)(surveys__isnull=not value).distinct()


# ─────────────────────────────────────────────────────────────────────────────
# HouseholdSurveyFilter
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdSurveyFilter(django_filters.FilterSet):
    """
    Multi-year and location filters for HouseholdSurvey records.

    Params:
        year             — exact survey year
        year_min         — survey year >= value
        year_max         — survey year <= value
        years            — comma-separated list (2022,2023,2024)
        status           — DRAFT | SUBMITTED | VERIFIED | REVISION
        purok            — Purok.number
        purok_id         — Purok UUID
        household_number — household_number icontains
        surveyed_by      — staff user PK who conducted the survey
        verified         — true = only VERIFIED surveys
    """
    year             = django_filters.NumberFilter(
        field_name='survey_year',
        label='Exact year',
    )
    year_min         = django_filters.NumberFilter(
        field_name='survey_year',
        lookup_expr='gte',
        label='Year from (inclusive)',
    )
    year_max         = django_filters.NumberFilter(
        field_name='survey_year',
        lookup_expr='lte',
        label='Year to (inclusive)',
    )
    years            = django_filters.BaseInFilter(
        field_name='survey_year',
        label='Multiple years (comma-separated: 2022,2023,2024)',
    )
    status           = django_filters.ChoiceFilter(
        choices=HouseholdSurvey.SurveyStatus.choices,
    )
    purok            = django_filters.NumberFilter(
        field_name='household__purok__number',
        label='Purok number',
    )
    purok_id         = django_filters.UUIDFilter(
        field_name='household__purok',
        label='Purok UUID',
    )
    household_number = django_filters.CharFilter(
        field_name='household__household_number',
        lookup_expr='icontains',
        label='Household number (partial)',
    )
    surveyed_by      = django_filters.NumberFilter(
        field_name='surveyed_by',
        label='Surveyed by (user PK)',
    )
    verified         = django_filters.BooleanFilter(
        method='filter_verified',
        label='Only verified surveys',
    )

    class Meta:
        model  = HouseholdSurvey
        fields = ['survey_year', 'status']

    def filter_verified(self, qs, name, value):
        if value:
            return qs.filter(status=HouseholdSurvey.SurveyStatus.VERIFIED)
        return qs.exclude(status=HouseholdSurvey.SurveyStatus.VERIFIED)


# ─────────────────────────────────────────────────────────────────────────────
# FamilyFilter
# ─────────────────────────────────────────────────────────────────────────────

class FamilyFilter(django_filters.FilterSet):
    """
    Filter Family records by income, survey year, and location.

    Params:
        household_survey — survey UUID
        income_bracket   — NO_INCOME | BELOW_5K | 5K_10K | ...
        survey_year      — year of parent survey
        purok            — Purok.number
        purok_id         — Purok UUID
    """
    household_survey = django_filters.UUIDFilter(field_name='household_survey')
    income_bracket   = django_filters.ChoiceFilter(
        field_name='monthly_income_bracket',
        choices=Family.IncomeBracket.choices,
        label='Income bracket',
    )
    survey_year      = django_filters.NumberFilter(
        field_name='household_survey__survey_year',
    )
    purok            = django_filters.NumberFilter(
        field_name='household_survey__household__purok__number',
    )
    purok_id         = django_filters.UUIDFilter(
        field_name='household_survey__household__purok',
    )

    class Meta:
        model  = Family
        fields = ['monthly_income_bracket']


# ─────────────────────────────────────────────────────────────────────────────
# PersonFilter
# ─────────────────────────────────────────────────────────────────────────────

class PersonFilter(django_filters.FilterSet):
    """
    Demographic filters for Person records.

    Params:
        name                    — partial match on first/last/middle name
        gender                  — MALE | FEMALE | OTHER
        civil_status            — SINGLE | MARRIED | WIDOWED | ...
        educational_attainment  — NO_FORMAL | KINDER | ELEM | ...
        role                    — HEAD | SPOUSE | CHILD | PARENT | ...
        is_registered_voter     — true | false
        sector                  — single sector code (PWD, SENIOR, 4PS, ...)
        age_min                 — minimum age (uses age_at_survey, falls back to DOB)
        age_max                 — maximum age
        survey_year             — year of parent survey
        purok                   — Purok.number
        purok_id                — Purok UUID
        household_number        — partial match on household_number

    Age filtering notes:
        age_at_survey is preferred because it preserves the age at the time
        of the survey, not the person's current age. A 2024 survey record
        where a person was 64 should still match age_min=60 regardless of
        what year you run the query in 2026.
        If age_at_survey is null, falls back to date_of_birth calculation.
    """
    name                   = django_filters.CharFilter(
        method='filter_name',
        label='Name (partial — searches first, last, middle)',
    )
    gender                 = django_filters.ChoiceFilter(choices=Person.Gender.choices)
    civil_status           = django_filters.ChoiceFilter(choices=Person.CivilStatus.choices)
    educational_attainment = django_filters.ChoiceFilter(
        choices=Person.EducationalAttainment.choices,
    )
    role                   = django_filters.ChoiceFilter(choices=Person.Role.choices)
    is_registered_voter    = django_filters.BooleanFilter()
    sector                 = django_filters.CharFilter(
        method='filter_sector',
        label='Sector code (e.g. PWD, 4PS, SENIOR)',
    )
    sectors                = django_filters.CharFilter(
        method='filter_sectors_any',
        label='Multiple sectors (comma-separated: PWD,SENIOR)',
    )
    age_min                = django_filters.NumberFilter(
        method='filter_age_min',
        label='Minimum age at survey',
    )
    age_max                = django_filters.NumberFilter(
        method='filter_age_max',
        label='Maximum age at survey',
    )
    survey_year            = django_filters.NumberFilter(
        field_name='family__household_survey__survey_year',
    )
    purok                  = django_filters.NumberFilter(
        field_name='family__household_survey__household__purok__number',
    )
    purok_id               = django_filters.UUIDFilter(
        field_name='family__household_survey__household__purok',
    )
    household_number       = django_filters.CharFilter(
        field_name='family__household_survey__household__household_number',
        lookup_expr='icontains',
    )

    class Meta:
        model  = Person
        fields = ['gender', 'civil_status', 'educational_attainment', 'role']

    def filter_name(self, qs, name, value):
        return qs.filter(
            Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(middle_name__icontains=value)
        )

    def filter_sector(self, qs, name, value):
        """
        JSON containment: matches persons who have this sector code in their
        sectors array.

        Uses GIN index path (sectors @> '["value"]') for O(log n) performance.
        """
        return qs.filter(sectors__contains=[value.strip().upper()])

    def filter_sectors_any(self, qs, name, value):
        """
        Match persons who have ANY of the given sector codes.
        Input: comma-separated string e.g. "PWD,SENIOR"
        """
        codes = [s.strip().upper() for s in value.split(',') if s.strip()]
        if not codes:
            return qs
        # OR-chain: has PWD OR has SENIOR
        q = Q()
        for code in codes:
            q |= Q(sectors__contains=[code])
        return qs.filter(q)

    def filter_age_min(self, qs, name, value):
        """
        Prefers age_at_survey (snapshot). Falls back to DOB-derived age.
        """
        current_year = date.today().year
        return qs.filter(
            Q(age_at_survey__gte=value)
            | Q(
                age_at_survey__isnull=True,
                date_of_birth__year__lte=current_year - value,
            )
        )

    def filter_age_max(self, qs, name, value):
        current_year = date.today().year
        return qs.filter(
            Q(age_at_survey__lte=value)
            | Q(
                age_at_survey__isnull=True,
                date_of_birth__year__gte=current_year - value,
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# ProgramAvailedFilter
# ─────────────────────────────────────────────────────────────────────────────

class ProgramAvailedFilter(django_filters.FilterSet):
    """
    Filter ProgramAvailed records by type, date range, and location.

    Params:
        program_type — FINANCIAL | EDUCATIONAL | MEDICAL | LIVELIHOOD | 4PS | ...
        date_from    — date_availed >= YYYY-MM-DD
        date_to      — date_availed <= YYYY-MM-DD
        survey_year  — year of parent survey
        purok        — Purok.number
        family       — family UUID
        has_amount   — true = amount is not null/zero
    """
    program_type = django_filters.ChoiceFilter(choices=ProgramAvailed.ProgramType.choices)
    date_from    = django_filters.DateFilter(
        field_name='date_availed',
        lookup_expr='gte',
        label='Date availed from',
    )
    date_to      = django_filters.DateFilter(
        field_name='date_availed',
        lookup_expr='lte',
        label='Date availed to',
    )
    survey_year  = django_filters.NumberFilter(
        field_name='family__household_survey__survey_year',
    )
    purok        = django_filters.NumberFilter(
        field_name='family__household_survey__household__purok__number',
    )
    purok_id     = django_filters.UUIDFilter(
        field_name='family__household_survey__household__purok',
    )
    family       = django_filters.UUIDFilter(field_name='family')
    has_amount   = django_filters.BooleanFilter(
        method='filter_has_amount',
        label='Has a monetary amount recorded',
    )

    class Meta:
        model  = ProgramAvailed
        fields = ['program_type']

    def filter_has_amount(self, qs, name, value):
        if value:
            return qs.filter(amount__isnull=False, amount__gt=0)
        return qs.filter(Q(amount__isnull=True) | Q(amount=0))
