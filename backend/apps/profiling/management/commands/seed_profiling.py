"""
Management command: seed_profiling
────────────────────────────────────────────────────────────────────────────────
Creates the initial FormSchema and FieldMapping records needed to start using
the Household Profiling module.

Usage:
    python manage.py seed_profiling                  # seeds current year
    python manage.py seed_profiling --year 2025      # seeds specific year
    python manage.py seed_profiling --force          # re-creates if exists

What it creates:
    1. FieldMapping records  — canonical field definitions (the lookup table
       that normalises raw field names/values across survey years)
    2. FormSchema record     — the actual survey form for the given year,
       stored as a JSON schema that DynamicFormRenderer reads
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.profiling.models import FieldMapping, FormSchema


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CANONICAL FIELD DEFINITIONS
#
#     year_map structure (matches FieldMapping.year_map):
#       { "2024": { "field_name": "water_source", "value_map": { "raw": "canonical" } } }
#
#     canonical_options: stable list of all possible canonical values across years
#       [{ "value": "METERED", "label": "Metered / Level 3" }]
#
#     data_type choices: text | number | select | multiselect | boolean | date
# ─────────────────────────────────────────────────────────────────────────────

FIELD_MAPPINGS = [

    # ── Household-level ──────────────────────────────────────────────────────

    {
        'canonical_name': 'water_source',
        'label':          'Primary Water Source',
        'level':          'household',
        'data_type':      'select',
        'canonical_options': [
            {'value': 'NATURE_SPRING', 'label': 'Nature / Spring'},
            {'value': 'DEEP_WELL',     'label': 'Poso / Deep Well'},
            {'value': 'METERED',       'label': 'Metered (Level 3)'},
            {'value': 'SHARED_TAP',    'label': 'Shared Tap (Level 2)'},
            {'value': 'BOTTLED',       'label': 'Bottled Water'},
        ],
        'year_map': {
            '2024': {
                'field_name': 'water_source',
                'value_map': {
                    'NATURE_SPRING': 'NATURE_SPRING',
                    'DEEP_WELL':     'DEEP_WELL',
                    'METERED':       'METERED',
                    'SHARED_TAP':    'SHARED_TAP',
                    'BOTTLED':       'BOTTLED',
                },
            },
            '2025': {
                'field_name': 'water_source',
                'value_map': {
                    'NATURE_SPRING': 'NATURE_SPRING',
                    'DEEP_WELL':     'DEEP_WELL',
                    'METERED':       'METERED',
                    'SHARED_TAP':    'SHARED_TAP',
                    'BOTTLED':       'BOTTLED',
                },
            },
        },
    },
    {
        'canonical_name': 'electricity_source',
        'label':          'Electricity Source',
        'level':          'household',
        'data_type':      'select',
        'canonical_options': [
            {'value': 'NONE',         'label': 'None'},
            {'value': 'SOLAR',        'label': 'Solar Panel'},
            {'value': 'METERED',      'label': 'Metered (POCO/BLCI)'},
            {'value': 'SHARED_METER', 'label': 'Shared Meter'},
        ],
        'year_map': {
            '2024': {
                'field_name': 'electricity_source',
                'value_map': {
                    'NONE': 'NONE', 'SOLAR': 'SOLAR',
                    'METERED': 'METERED', 'SHARED_METER': 'SHARED_METER',
                },
            },
            '2025': {
                'field_name': 'electricity_source',
                'value_map': {
                    'NONE': 'NONE', 'SOLAR': 'SOLAR',
                    'METERED': 'METERED', 'SHARED_METER': 'SHARED_METER',
                },
            },
        },
    },
    {
        'canonical_name': 'toilet_type',
        'label':          'Toilet Facility',
        'level':          'household',
        'data_type':      'select',
        'canonical_options': [
            {'value': 'NONE',        'label': 'None'},
            {'value': 'SHARED',      'label': 'Shared Toilet'},
            {'value': 'FLUSH',       'label': 'Water-sealed / Flush'},
            {'value': 'PIT_LATRINE', 'label': 'Pit Latrine'},
        ],
        'year_map': {
            '2024': {
                'field_name': 'toilet_type',
                'value_map': {
                    'NONE': 'NONE', 'SHARED': 'SHARED',
                    'FLUSH': 'FLUSH', 'PIT_LATRINE': 'PIT_LATRINE',
                },
            },
            '2025': {
                'field_name': 'toilet_type',
                'value_map': {
                    'NONE': 'NONE', 'SHARED': 'SHARED',
                    'FLUSH': 'FLUSH', 'PIT_LATRINE': 'PIT_LATRINE',
                },
            },
        },
    },
    {
        'canonical_name': 'house_ownership',
        'label':          'House Ownership',
        'level':          'household',
        'data_type':      'select',
        'canonical_options': [
            {'value': 'OWNED',            'label': 'Owned'},
            {'value': 'RENTED',           'label': 'Rented'},
            {'value': 'SHARED',           'label': 'Shared / Staying with Relatives'},
            {'value': 'INFORMAL_SETTLER', 'label': 'Informal Settler'},
        ],
        'year_map': {
            '2024': {
                'field_name': 'house_ownership',
                'value_map': {
                    'OWNED': 'OWNED', 'RENTED': 'RENTED',
                    'SHARED': 'SHARED', 'INFORMAL_SETTLER': 'INFORMAL_SETTLER',
                },
            },
            '2025': {
                'field_name': 'house_ownership',
                'value_map': {
                    'OWNED': 'OWNED', 'RENTED': 'RENTED',
                    'SHARED': 'SHARED', 'INFORMAL_SETTLER': 'INFORMAL_SETTLER',
                },
            },
        },
    },
    {
        'canonical_name': 'internet_access',
        'label':          'Internet Access',
        'level':          'household',
        'data_type':      'boolean',
        'canonical_options': [],
        'year_map': {
            '2024': {'field_name': 'internet_access', 'value_map': {}},
            '2025': {'field_name': 'internet_access', 'value_map': {}},
        },
    },

    # ── Family-level ──────────────────────────────────────────────────────────

    {
        'canonical_name': 'monthly_income_bracket',
        'label':          'Monthly Income Bracket',
        'level':          'family',
        'data_type':      'select',
        'canonical_options': [
            {'value': 'NO_INCOME', 'label': 'No Income'},
            {'value': 'BELOW_5K',  'label': 'Below ₱5,000'},
            {'value': '5K_10K',    'label': '₱5,000 – ₱10,000'},
            {'value': '10K_20K',   'label': '₱10,000 – ₱20,000'},
            {'value': '20K_30K',   'label': '₱20,000 – ₱30,000'},
            {'value': '30K_50K',   'label': '₱30,000 – ₱50,000'},
            {'value': 'ABOVE_50K', 'label': 'Above ₱50,000'},
        ],
        'year_map': {
            '2024': {
                'field_name': 'monthly_income_bracket',
                'value_map': {
                    'NO_INCOME': 'NO_INCOME', 'BELOW_5K': 'BELOW_5K',
                    '5K_10K': '5K_10K', '10K_20K': '10K_20K',
                    '20K_30K': '20K_30K', '30K_50K': '30K_50K',
                    'ABOVE_50K': 'ABOVE_50K',
                },
            },
            '2025': {
                'field_name': 'monthly_income_bracket',
                'value_map': {
                    'NO_INCOME': 'NO_INCOME', 'BELOW_5K': 'BELOW_5K',
                    '5K_10K': '5K_10K', '10K_20K': '10K_20K',
                    '20K_30K': '20K_30K', '30K_50K': '30K_50K',
                    'ABOVE_50K': 'ABOVE_50K',
                },
            },
        },
    },

    # ── Person-level ──────────────────────────────────────────────────────────

    {
        'canonical_name': 'employment_status',
        'label':          'Employment Status',
        'level':          'person',
        'data_type':      'select',
        'canonical_options': [
            {'value': 'EMPLOYED',      'label': 'Employed'},
            {'value': 'SELF_EMPLOYED', 'label': 'Self-Employed'},
            {'value': 'UNEMPLOYED',    'label': 'Unemployed'},
            {'value': 'STUDENT',       'label': 'Student'},
            {'value': 'RETIRED',       'label': 'Retired'},
            {'value': 'TOO_YOUNG',     'label': 'Too Young (below 15)'},
        ],
        'year_map': {
            '2024': {
                'field_name': 'employment_status',
                'value_map': {
                    'EMPLOYED': 'EMPLOYED', 'SELF_EMPLOYED': 'SELF_EMPLOYED',
                    'UNEMPLOYED': 'UNEMPLOYED', 'STUDENT': 'STUDENT',
                    'RETIRED': 'RETIRED', 'TOO_YOUNG': 'TOO_YOUNG',
                },
            },
            '2025': {
                'field_name': 'employment_status',
                'value_map': {
                    'EMPLOYED': 'EMPLOYED', 'SELF_EMPLOYED': 'SELF_EMPLOYED',
                    'UNEMPLOYED': 'UNEMPLOYED', 'STUDENT': 'STUDENT',
                    'RETIRED': 'RETIRED', 'TOO_YOUNG': 'TOO_YOUNG',
                },
            },
        },
    },
    {
        'canonical_name': 'is_4ps_beneficiary',
        'label':          '4Ps Beneficiary',
        'level':          'person',
        'data_type':      'boolean',
        'canonical_options': [],
        'year_map': {
            '2024': {'field_name': 'is_4ps_beneficiary', 'value_map': {}},
            '2025': {'field_name': 'is_4ps_beneficiary', 'value_map': {}},
        },
    },
    {
        'canonical_name': 'has_philhealth',
        'label':          'PhilHealth Member',
        'level':          'person',
        'data_type':      'boolean',
        'canonical_options': [],
        'year_map': {
            '2024': {'field_name': 'has_philhealth', 'value_map': {}},
            '2025': {'field_name': 'has_philhealth', 'value_map': {}},
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 2.  FORM SCHEMA
#
#     { sections: [{ id, label, level, fields: [...] }] }
#     field.type: text | number | select | multiselect | date | boolean | textarea
#     field.canonical: links to a FieldMapping.canonical_name (can be null)
# ─────────────────────────────────────────────────────────────────────────────

def build_schema(year):
    return {
        'sections': [

            # ── Housing & Facilities (fills HouseholdSurvey.data) ─────────────
            {
                'id':    'housing',
                'label': 'Housing & Facilities',
                'level': 'household',
                'fields': [
                    {
                        'id': 'water_source', 'canonical': 'water_source',
                        'label': 'Primary Water Source', 'type': 'select', 'required': True,
                        'options': [
                            {'value': 'NATURE_SPRING', 'label': 'Nature / Spring'},
                            {'value': 'DEEP_WELL',     'label': 'Poso / Deep Well'},
                            {'value': 'METERED',       'label': 'Metered (Level 3)'},
                            {'value': 'SHARED_TAP',    'label': 'Shared Tap (Level 2)'},
                            {'value': 'BOTTLED',       'label': 'Bottled Water'},
                        ],
                        'help_text': 'Main source of drinking water',
                    },
                    {
                        'id': 'electricity_source', 'canonical': 'electricity_source',
                        'label': 'Electricity Source', 'type': 'select', 'required': True,
                        'options': [
                            {'value': 'NONE',         'label': 'None'},
                            {'value': 'SOLAR',        'label': 'Solar Panel'},
                            {'value': 'METERED',      'label': 'Metered (POCO/BLCI)'},
                            {'value': 'SHARED_METER', 'label': 'Shared Meter'},
                        ],
                    },
                    {
                        'id': 'toilet_type', 'canonical': 'toilet_type',
                        'label': 'Toilet Facility', 'type': 'select', 'required': True,
                        'options': [
                            {'value': 'NONE',        'label': 'None'},
                            {'value': 'SHARED',      'label': 'Shared Toilet'},
                            {'value': 'FLUSH',       'label': 'Water-sealed / Flush'},
                            {'value': 'PIT_LATRINE', 'label': 'Pit Latrine'},
                        ],
                    },
                    {
                        'id': 'house_ownership', 'canonical': 'house_ownership',
                        'label': 'House Ownership', 'type': 'select', 'required': True,
                        'options': [
                            {'value': 'OWNED',            'label': 'Owned'},
                            {'value': 'RENTED',           'label': 'Rented'},
                            {'value': 'SHARED',           'label': 'Shared / Relatives'},
                            {'value': 'INFORMAL_SETTLER', 'label': 'Informal Settler'},
                        ],
                    },
                    {
                        'id': 'lot_ownership', 'canonical': None,
                        'label': 'Lot Ownership', 'type': 'select', 'required': False,
                        'options': [
                            {'value': 'OWNED',       'label': 'Owned'},
                            {'value': 'RENTED',      'label': 'Rented'},
                            {'value': 'SHARED',      'label': 'Shared'},
                            {'value': 'PUBLIC_LAND', 'label': 'Public Land'},
                        ],
                    },
                    {
                        'id': 'house_materials', 'canonical': None,
                        'label': 'Main House Materials', 'type': 'select', 'required': False,
                        'options': [
                            {'value': 'CONCRETE',  'label': 'Concrete / Hollow Blocks'},
                            {'value': 'WOOD',      'label': 'Wood'},
                            {'value': 'MIXED',     'label': 'Mixed (Concrete + Wood)'},
                            {'value': 'LIGHT',     'label': 'Light Materials (Bamboo/Nipa)'},
                            {'value': 'MAKESHIFT', 'label': 'Makeshift / Salvaged'},
                        ],
                    },
                    {
                        'id': 'num_rooms', 'canonical': None,
                        'label': 'Number of Rooms', 'type': 'number', 'required': False,
                        'help_text': 'Excluding bathroom',
                    },
                    {
                        'id': 'internet_access', 'canonical': 'internet_access',
                        'label': 'Has Internet Access', 'type': 'boolean', 'required': False,
                        'help_text': 'Any internet connection (mobile data, broadband, etc.)',
                    },
                ],
            },

            # ── Livelihood (extra data stored in Family.data) ─────────────────
            {
                'id':    'livelihood',
                'label': 'Livelihood & Additional Info',
                'level': 'family',
                'fields': [
                    {
                        'id': 'main_livelihood', 'canonical': None,
                        'label': 'Main Source of Income', 'type': 'select', 'required': False,
                        'options': [
                            {'value': 'FARMING',    'label': 'Farming / Agriculture'},
                            {'value': 'FISHING',    'label': 'Fishing'},
                            {'value': 'LABOR',      'label': 'Labor / Construction'},
                            {'value': 'BUSINESS',   'label': 'Small Business / Vending'},
                            {'value': 'EMPLOYED',   'label': 'Employed (Private/Gov)'},
                            {'value': 'REMITTANCE', 'label': 'Remittance (OFW)'},
                            {'value': 'PENSION',    'label': 'Pension / SSS / GSIS'},
                            {'value': 'NONE',       'label': 'None'},
                        ],
                    },
                    {
                        'id': 'family_remarks', 'canonical': None,
                        'label': 'Remarks / Notes', 'type': 'textarea',
                        'required': False, 'cols': 2,
                        'help_text': 'Any additional notes about this family',
                    },
                ],
            },

            # ── Person extra fields (stored in Person.data) ───────────────────
            {
                'id':    'person_extra',
                'label': 'Person — Additional Information',
                'level': 'person',
                'fields': [
                    {
                        'id': 'employment_status', 'canonical': 'employment_status',
                        'label': 'Employment Status', 'type': 'select', 'required': False,
                        'options': [
                            {'value': 'EMPLOYED',      'label': 'Employed'},
                            {'value': 'SELF_EMPLOYED', 'label': 'Self-Employed'},
                            {'value': 'UNEMPLOYED',    'label': 'Unemployed'},
                            {'value': 'STUDENT',       'label': 'Student'},
                            {'value': 'RETIRED',       'label': 'Retired'},
                            {'value': 'TOO_YOUNG',     'label': 'Too Young (below 15)'},
                        ],
                    },
                    {
                        'id': 'is_4ps_beneficiary', 'canonical': 'is_4ps_beneficiary',
                        'label': '4Ps Beneficiary', 'type': 'boolean', 'required': False,
                    },
                    {
                        'id': 'has_philhealth', 'canonical': 'has_philhealth',
                        'label': 'PhilHealth Member', 'type': 'boolean', 'required': False,
                    },
                    {
                        'id': 'has_sss', 'canonical': None,
                        'label': 'SSS Member', 'type': 'boolean', 'required': False,
                    },
                    {
                        'id': 'remarks', 'canonical': None,
                        'label': 'Remarks', 'type': 'textarea',
                        'required': False, 'cols': 2,
                    },
                ],
            },
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Command
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seeds initial FormSchema and FieldMapping records for the profiling module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year', type=int,
            default=timezone.now().year,
            help='Survey year to create the schema for (default: current year)',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Re-create the schema even if one already exists for this year',
        )

    def handle(self, *args, **options):
        year  = options['year']
        force = options['force']

        # ── 1. FieldMappings ─────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('\n[1/2] Seeding FieldMappings…'))
        created_fm = updated_fm = 0

        for fm in FIELD_MAPPINGS:
            obj, created = FieldMapping.objects.update_or_create(
                canonical_name=fm['canonical_name'],
                defaults={
                    'label':             fm['label'],
                    'level':             fm['level'],
                    'data_type':         fm['data_type'],
                    'canonical_options': fm.get('canonical_options', []),
                    'year_map':          fm.get('year_map', {}),
                },
            )
            if created:
                created_fm += 1
            else:
                updated_fm += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'    FieldMappings: {created_fm} created, {updated_fm} updated'
            )
        )

        # ── 2. FormSchema ────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO(f'\n[2/2] Seeding FormSchema for year {year}…'))

        existing = FormSchema.objects.filter(year=year, is_active=True).first()
        if existing and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'    FormSchema for {year} already exists: "{existing.name}" (id={existing.id})\n'
                    f'    Run with --force to overwrite.'
                )
            )
        else:
            if force and existing:
                existing.delete()
                self.stdout.write(self.style.WARNING('    Deleted existing schema (--force).'))

            schema = FormSchema.objects.create(
                year=year,
                version=1,
                name=f'Barangay Household Survey {year}',
                description=(
                    f'Standard household profiling survey form for {year}. '
                    f'Covers housing facilities, livelihood, and person demographics.'
                ),
                schema=build_schema(year),
                is_active=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'    FormSchema created: "{schema.name}" (id={schema.id})'
                )
            )

        self.stdout.write(self.style.SUCCESS('\nProfiling seed complete.\n'))
