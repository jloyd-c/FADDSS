"""
Profiling App — Django Signals
══════════════════════════════════════════════════════════════════════════════

PURPOSE
───────
Auto-populate the NormalizedData table after any survey, family, or person
record is saved. This keeps the cross-year query layer in sync with the
source data at all times without requiring manual management.

HOW IT WORKS
────────────
1. post_save fires on HouseholdSurvey / Family / Person
2. Signal schedules normalization via transaction.on_commit()
   → runs AFTER the DB transaction commits, so a normalization failure
     can never roll back the actual survey save
3. Normalization function:
   a. Deletes existing NormalizedData rows for this record+level
   b. Reads the data JSON field
   c. Maps each field_id → canonical_name  (via FormSchema.get_canonical_map)
   d. Maps each raw_value → canonical_value (via FieldMapping.get_canonical_value)
   e. Bulk-inserts new NormalizedData rows

WHAT HAPPENS ON FAILURE
────────────────────────
Normalization failures are logged but do not raise exceptions.
The survey data is always the source of truth. NormalizedData can be
fully regenerated at any time by running:
    python manage.py shell
    >>> from apps.profiling.signals import rebuild_normalized_data_for_survey
    >>> for s in HouseholdSurvey.all_objects.all():
    ...     rebuild_normalized_data_for_survey(s)

SKIPPED FIELDS
──────────────
- Null or empty values are skipped (no row inserted)
- Fields with no corresponding FieldMapping are skipped
- Multiselect values (lists) are stored as JSON strings in raw_value/canonical_value
"""

import json
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Family, FieldMapping, HouseholdSurvey, NormalizedData, Person

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _load_field_mappings() -> dict[str, FieldMapping]:
    """
    Load ALL FieldMapping records into a dict keyed by canonical_name.

    Called once per normalization run. In production with many field
    mappings, consider caching this with Django's cache framework.

    Returns:
        {'water_source': <FieldMapping>, 'electricity_source': <FieldMapping>, ...}
    """
    return {fm.canonical_name: fm for fm in FieldMapping.objects.all()}


def _coerce_to_str(value) -> str:
    """
    Convert any value to a string suitable for storage in NormalizedData.

    Lists (multiselect) and dicts become JSON strings.
    Everything else is cast to str.
    """
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _build_rows(
    survey: HouseholdSurvey,
    level: str,
    source_id,               # UUID | None
    data: dict,
    canonical_map: dict,     # {field_id: canonical_name}
    field_mappings: dict,    # {canonical_name: FieldMapping}
) -> list[NormalizedData]:
    """
    Build a list of unsaved NormalizedData rows for a single data dict.

    Args:
        survey:         The parent HouseholdSurvey
        level:          'household' | 'family' | 'person'
        source_id:      Family.id or Person.id (None for household-level)
        data:           The JSON data dict from the model instance
        canonical_map:  {field_id → canonical_name} from FormSchema
        field_mappings: {canonical_name → FieldMapping} from DB

    Returns:
        List of NormalizedData instances (not yet saved)
    """
    rows = []
    year = survey.survey_year

    for field_id, raw_value in data.items():
        # Skip empty / null values — no useful information to normalize
        if raw_value is None or raw_value == '' or raw_value == []:
            continue

        # Resolve field_id → canonical_name
        canonical_name = canonical_map.get(field_id)
        if not canonical_name:
            # Field exists in form but has no canonical mapping → skip
            # This is expected for new/experimental fields not yet in FieldMapping
            continue

        # Resolve FieldMapping for this canonical concept
        fm = field_mappings.get(canonical_name)
        if fm is None:
            # canonical_name in schema but no FieldMapping row → skip
            # Operator needs to add the mapping; silent skip prevents noisy logs
            continue

        raw_str       = _coerce_to_str(raw_value)
        canonical_str = _coerce_to_str(
            fm.get_canonical_value(year, raw_str)
        )

        rows.append(NormalizedData(
            household_survey=survey,
            survey_year=year,
            level=level,
            source_id=source_id,
            canonical_name=canonical_name,
            raw_value=raw_str[:500],        # CharField max_length=500
            canonical_value=canonical_str[:500],
        ))

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Core normalization functions
# ─────────────────────────────────────────────────────────────────────────────

def normalize_survey_household_level(survey: HouseholdSurvey) -> int:
    """
    Refresh NormalizedData for the household-level fields of one survey.

    Deletes existing household-level rows for this survey and inserts fresh
    ones derived from the current HouseholdSurvey.data.

    Returns:
        Number of NormalizedData rows inserted.
    """
    # Delete stale rows for household-level data of this survey
    NormalizedData.objects.filter(
        household_survey=survey,
        level='household',
    ).delete()

    if not survey.data:
        return 0

    canonical_map  = survey.form_schema.get_canonical_map()
    field_mappings = _load_field_mappings()

    rows = _build_rows(
        survey=survey,
        level='household',
        source_id=None,
        data=survey.data,
        canonical_map=canonical_map,
        field_mappings=field_mappings,
    )

    if rows:
        NormalizedData.objects.bulk_create(rows)

    return len(rows)


def normalize_family_level(family: Family) -> int:
    """
    Refresh NormalizedData for the family-level fields of one Family.

    Deletes existing family-level rows for this family+survey pair and
    inserts fresh ones from Family.data.

    Returns:
        Number of NormalizedData rows inserted.
    """
    survey = family.household_survey

    NormalizedData.objects.filter(
        household_survey=survey,
        level='family',
        source_id=family.id,
    ).delete()

    if not family.data:
        return 0

    canonical_map  = survey.form_schema.get_canonical_map()
    field_mappings = _load_field_mappings()

    rows = _build_rows(
        survey=survey,
        level='family',
        source_id=family.id,
        data=family.data,
        canonical_map=canonical_map,
        field_mappings=field_mappings,
    )

    if rows:
        NormalizedData.objects.bulk_create(rows)

    return len(rows)


def normalize_person_level(person: Person) -> int:
    """
    Refresh NormalizedData for the person-level fields of one Person.

    Deletes existing person-level rows for this person+survey pair and
    inserts fresh ones from Person.data.

    Returns:
        Number of NormalizedData rows inserted.
    """
    survey = person.family.household_survey

    NormalizedData.objects.filter(
        household_survey=survey,
        level='person',
        source_id=person.id,
    ).delete()

    if not person.data:
        return 0

    canonical_map  = survey.form_schema.get_canonical_map()
    field_mappings = _load_field_mappings()

    rows = _build_rows(
        survey=survey,
        level='person',
        source_id=person.id,
        data=person.data,
        canonical_map=canonical_map,
        field_mappings=field_mappings,
    )

    if rows:
        NormalizedData.objects.bulk_create(rows)

    return len(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Full rebuild utility (management command / admin action)
# ─────────────────────────────────────────────────────────────────────────────

def rebuild_normalized_data_for_survey(survey: HouseholdSurvey) -> dict:
    """
    Fully regenerate ALL NormalizedData for one survey and all its
    families and persons.

    Use this in:
    - A management command to backfill after adding new FieldMappings
    - An admin action to re-sync after manual data corrections
    - Tests to assert normalization is correct

    Usage:
        from apps.profiling.signals import rebuild_normalized_data_for_survey
        result = rebuild_normalized_data_for_survey(survey)
        # {'household': 8, 'families': 12, 'persons': 34}

    Returns:
        Dict with counts of rows inserted per level.
    """
    # Use select_related/prefetch to avoid N+1 queries
    survey = (
        HouseholdSurvey.all_objects
        .select_related('form_schema')
        .prefetch_related(
            'families__persons',
        )
        .get(pk=survey.pk)
    )

    household_count = normalize_survey_household_level(survey)
    family_count    = 0
    person_count    = 0

    for family in survey.families.all():
        family_count += normalize_family_level(family)
        for person in family.persons.all():
            person_count += normalize_person_level(person)

    return {
        'household': household_count,
        'families':  family_count,
        'persons':   person_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Signal handlers
# ─────────────────────────────────────────────────────────────────────────────

@receiver(post_save, sender=HouseholdSurvey)
def on_household_survey_save(sender, instance, **kwargs):
    """
    After a HouseholdSurvey is saved, refresh its household-level
    NormalizedData rows.

    Uses transaction.on_commit() so:
    1. Normalization runs AFTER the outer DB transaction commits
    2. A normalization failure never rolls back the survey save
    3. The fresh DB row is visible to the normalization query

    The survey is re-fetched inside the callback to get the latest data
    (important if the post_save fires mid-transaction with stale state).
    """
    survey_id = instance.pk

    def run():
        try:
            survey = HouseholdSurvey.all_objects.select_related(
                'form_schema'
            ).get(pk=survey_id)
            normalize_survey_household_level(survey)
        except HouseholdSurvey.DoesNotExist:
            # Survey was deleted before on_commit fired — nothing to do
            pass
        except Exception:
            logger.exception(
                '[NormalizedData] Failed to normalize household survey pk=%s',
                survey_id
            )

    transaction.on_commit(run)


@receiver(post_save, sender=Family)
def on_family_save(sender, instance, **kwargs):
    """
    After a Family is saved, refresh its family-level NormalizedData rows.
    """
    family_id = instance.pk

    def run():
        try:
            family = Family.all_objects.select_related(
                'household_survey__form_schema'
            ).get(pk=family_id)
            normalize_family_level(family)
        except Family.DoesNotExist:
            pass
        except Exception:
            logger.exception(
                '[NormalizedData] Failed to normalize family pk=%s',
                family_id
            )

    transaction.on_commit(run)


@receiver(post_save, sender=Person)
def on_person_save(sender, instance, **kwargs):
    """
    After a Person is saved, refresh their person-level NormalizedData rows.
    """
    person_id = instance.pk

    def run():
        try:
            person = Person.all_objects.select_related(
                'family__household_survey__form_schema'
            ).get(pk=person_id)
            normalize_person_level(person)
        except Person.DoesNotExist:
            pass
        except Exception:
            logger.exception(
                '[NormalizedData] Failed to normalize person pk=%s',
                person_id
            )

    transaction.on_commit(run)
