"""
Profiling App — ViewSets (Phase 3)
══════════════════════════════════════════════════════════════════════════════

COMPLETE URL MAP (all under /api/v1/profiling/)
────────────────────────────────────────────────
  households/                              GET list, POST create
  households/{id}/                         GET detail, PATCH update, DELETE soft-delete
  households/{id}/surveys/                 GET all surveys for this household
  households/{id}/latest-survey/           GET most recent survey
  households/{id}/compare/                 GET diff (?year_a=2024&year_b=2025)
  households/{id}/change-log/             GET audit trail

  surveys/                                 GET list (filterable), POST create (nested)
  surveys/{id}/                            GET detail, PATCH update data
  surveys/{id}/submit/                     POST DRAFT|REVISION → SUBMITTED
  surveys/{id}/verify/                     POST SUBMITTED → VERIFIED  (ADMIN+)
  surveys/{id}/request-revision/           POST SUBMITTED → REVISION  (ADMIN+)

  families/                                GET list, filter by household_survey
  families/{id}/                           GET detail, PATCH update

  persons/                                 GET list (filterable + searchable)
  persons/{id}/                            GET detail, PATCH update

  programs/                                GET list, POST create, PATCH, DELETE
  programs/{id}/                           …

  schemas/                                 GET list, POST (ADMIN+)
  schemas/{id}/                            GET detail, PATCH (ADMIN+)

  mappings/                                GET list, POST (ADMIN+)
  mappings/{id}/                           GET detail, PATCH (ADMIN+)

  query/filter-by-concept/                 GET cross-year concept filter
  query/get-trend/                         GET year-over-year count
  query/demographics/                      GET demographic summary
  query/concepts/                          GET list available FieldMapping concepts
  query/concept-values/                    GET unique values for one concept+year

  reports/export/                          GET download (CSV/Excel)
  reports/rebuild-normalized/             POST trigger NormalizedData rebuild (ADMIN+)

PERMISSION MODEL (Phase 3)
──────────────────────────
  CanEncodeSurvey   — create/edit surveys: ADMIN+ or STAFF with can_create|can_edit
  CanViewSurvey     — read-only surveys: ADMIN+ or STAFF with can_view
  IsAdmin           — ADMIN/SUPER_ADMIN only (verify, schema mgmt, etc.)
  include_deleted=true — only ADMIN+ may request deleted records in exports

FILTER BACKENDS
───────────────
  DjangoFilterBackend — filterset_class handles field-specific filters
  SearchFilter        — ?search= searches common text fields
  OrderingFilter      — ?ordering= sorts by allowed fields
"""

import logging

from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.common.permissions import (
    CanDeleteSurvey,
    CanEncodeSurvey,
    CanExportSurvey,
    CanViewSurvey,
    IsAdmin,
    IsStaff,
    NotForcingPasswordChange,
)

from .filters import (
    FamilyFilter,
    HouseholdFilter,
    HouseholdSurveyFilter,
    PersonFilter,
    ProgramAvailedFilter,
)
from .models import (
    Family, FieldMapping, FormSchema, Household,
    HouseholdChangeLog, HouseholdSurvey, NormalizedData, Person,
    ProgramAvailed,
)
from .pagination import ProfilingPagination
from .serializers import (
    CreateSurveySerializer,
    FamilySerializer,
    FamilyUpdateSerializer,
    FieldMappingSerializer,
    FormSchemaSerializer,
    HouseholdChangeLogSerializer,
    HouseholdSerializer,
    HouseholdSurveyLightSerializer,
    HouseholdSurveySerializer,
    HouseholdWriteSerializer,
    NormalizedDataSerializer,
    PersonSerializer,
    PersonUpdateSerializer,
    ProgramAvailedSerializer,
    ProgramAvailedWriteSerializer,
    SurveyDataUpdateSerializer,
)
from .services import (
    HouseholdService,
    InvalidStatusTransitionError,
    NormalizationService,
    QueryService,
    ReportService,
    SurveyAlreadyExistsError,
    SurveyImmutableError,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Mixin: purok-scoped queryset for Staff
# ─────────────────────────────────────────────────────────────────────────────

_ACTION_TO_PERM = {
    'list':           'can_view',
    'retrieve':       'can_view',
    'create':         'can_create',
    'partial_update': 'can_edit',
    'update':         'can_edit',
    'destroy':        'can_delete',
}


class PurokScopedMixin:
    """
    Restricts STAFF queryset to households in their assigned puroks.
    ADMIN+ sees everything.

    Also supports `?include_deleted=true` for ADMIN+ users to access
    soft-deleted records in list/retrieve actions.
    """

    def _allowed_purok_ids(self, perm_flag: str) -> list | None:
        """None = no restriction (ADMIN+). Empty list = no access."""
        user = self.request.user
        if user.role in ('SUPER_ADMIN', 'ADMIN'):
            return None
        if user.role == 'STAFF':
            return list(
                user.purok_permissions.filter(**{perm_flag: True})
                .values_list('purok_id', flat=True)
            )
        return []

    def _perm_flag_for_action(self) -> str:
        return _ACTION_TO_PERM.get(self.action, 'can_view')

    def _include_deleted(self) -> bool:
        """
        Returns True only if ADMIN+ explicitly requests deleted records.
        Staff cannot access deleted records even with include_deleted=true.
        """
        user = self.request.user
        if user.role not in ('SUPER_ADMIN', 'ADMIN'):
            return False
        raw = self.request.query_params.get('include_deleted', 'false')
        return raw.lower() in ('true', '1', 'yes')


# ─────────────────────────────────────────────────────────────────────────────
# HouseholdViewSet
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdViewSet(PurokScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for Household records.

    Filters:  ?purok=3&status=ACTIVE&surveyed_year=2024
    Search:   ?search=household_number_or_address
    Order:    ?ordering=household_number | purok__number | created_at
    Admin:    ?include_deleted=true  (ADMIN+ only)
    """
    http_method_names  = ['get', 'post', 'patch', 'delete', 'head', 'options']
    pagination_class   = ProfilingPagination
    filterset_class    = HouseholdFilter
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['household_number', 'address', 'purok__name']
    ordering_fields    = ['household_number', 'purok__number', 'status', 'created_at']
    ordering           = ['purok__number', 'household_number']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin(), NotForcingPasswordChange()]
        if self.action in ('list', 'retrieve', 'surveys', 'latest_survey',
                           'compare', 'change_log'):
            return [CanViewSurvey(), NotForcingPasswordChange()]
        return [CanEncodeSurvey(), NotForcingPasswordChange()]

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return HouseholdWriteSerializer
        return HouseholdSerializer

    def get_queryset(self):
        perm_flag = self._perm_flag_for_action()
        purok_ids = self._allowed_purok_ids(perm_flag)
        manager   = Household.all_objects if self._include_deleted() else Household.objects

        qs = manager.select_related('purok').order_by('purok__number', 'household_number')
        if purok_ids is not None:
            qs = qs.filter(purok_id__in=purok_ids)
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        household = HouseholdService.create_household(
            purok=data['purok'],
            address=data.get('address', ''),
            created_by=self.request.user,
            household_number=data.get('household_number') or None,
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            notes=data.get('notes', ''),
        )
        serializer.instance = household

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete(deleted_by_user=self.request.user)

    # ── Custom actions ───────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='my', permission_classes=[CanViewSurvey, NotForcingPasswordChange])
    def my_household(self, request):
        """
        GET /households/my/

        Returns the Household record that the authenticated RESIDENT belongs to.
        The RESIDENT must have a linked Person → Family → HouseholdSurvey → Household chain.

        Other roles receive a 403 — they use the standard list/retrieve endpoints.
        """
        if request.user.role != 'RESIDENT':
            raise PermissionDenied('This endpoint is only for Resident accounts.')
        if not request.user.person_id:
            raise NotFound('Your account is not linked to a person record.')

        try:
            household = (
                request.user.person
                .family
                .household_survey
                .household
            )
        except Exception:
            raise NotFound('Could not locate your household. Please contact an administrator.')

        # Enforce object-level permission (ensures resident owns this household)
        self.check_object_permissions(request, household)
        return Response(HouseholdSerializer(household).data)

    @action(detail=True, methods=['get'])
    def surveys(self, request, pk=None):
        """
        GET /households/{id}/surveys/
        All surveys for this household, newest first.
        Supports ?year_min=2022&year_max=2024 and ?status=VERIFIED.
        """
        household = self.get_object()
        qs = (
            HouseholdSurvey.objects
            .filter(household=household)
            .select_related('form_schema', 'surveyed_by')
            .order_by('-survey_year')
        )

        # Lightweight inline filtering on this sub-list
        year = request.query_params.get('year')
        if year:
            qs = qs.filter(survey_year=year)
        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                HouseholdSurveyLightSerializer(page, many=True).data
            )
        return Response(HouseholdSurveyLightSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='latest-survey')
    def latest_survey(self, request, pk=None):
        """GET /households/{id}/latest-survey/ — full detail of most recent survey."""
        household = self.get_object()
        survey = HouseholdService.get_latest_survey(household)
        if not survey:
            return Response(
                {'detail': 'No surveys found for this household.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(HouseholdSurveySerializer(survey).data)

    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """
        GET /households/{id}/compare/?year_a=2024&year_b=2025

        Returns a structured diff between two survey years.
        Uses NormalizedData for household-level canonical comparison
        and direct field comparison for family/person level.

        Query params:
            year_a (int, required)
            year_b (int, required)
        """
        household = self.get_object()

        year_a = request.query_params.get('year_a')
        year_b = request.query_params.get('year_b')
        if not year_a or not year_b:
            raise ValidationError({'detail': 'year_a and year_b are required.'})

        try:
            year_a, year_b = int(year_a), int(year_b)
        except ValueError:
            raise ValidationError({'detail': 'year_a and year_b must be integers.'})

        try:
            survey_a = HouseholdSurvey.objects.get(household=household, survey_year=year_a)
            survey_b = HouseholdSurvey.objects.get(household=household, survey_year=year_b)
        except HouseholdSurvey.DoesNotExist as exc:
            raise NotFound(str(exc))

        return Response(HouseholdService.compare_surveys(survey_a, survey_b))

    @action(detail=True, methods=['get'], url_path='change-log')
    def change_log(self, request, pk=None):
        """
        GET /households/{id}/change-log/
        Paginated audit trail for this household.

        Optional filters:
            ?target_type=SURVEY|FAMILY|PERSON|PROGRAM
            ?survey_year=2024
            ?action=CREATED|UPDATED|DELETED|VERIFIED|REVISION
        """
        household = self.get_object()
        qs = (
            HouseholdChangeLog.objects
            .filter(household=household)
            .select_related('changed_by')
            .order_by('-changed_at')
        )

        for param, field in [
            ('target_type', 'target_type'),
            ('survey_year', 'survey_year'),
            ('action',      'action'),
        ]:
            val = request.query_params.get(param)
            if val:
                qs = qs.filter(**{field: val})

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                HouseholdChangeLogSerializer(page, many=True).data
            )
        return Response(HouseholdChangeLogSerializer(qs, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# HouseholdSurveyViewSet
# ─────────────────────────────────────────────────────────────────────────────

class HouseholdSurveyViewSet(PurokScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for HouseholdSurveys + status transition actions.

    Filters:   ?year=2024  ?year_min=2022&year_max=2024  ?years=2022,2023,2024
               ?status=VERIFIED  ?purok=3  ?household_number=PRK3-2024-001
    Search:    ?search=household_number
    Order:     ?ordering=-survey_year | household__household_number | status
    Admin:     ?include_deleted=true
    """
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    pagination_class  = ProfilingPagination
    filterset_class   = HouseholdSurveyFilter
    filter_backends   = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields     = ['household__household_number', 'household__purok__name']
    ordering_fields   = ['survey_year', 'status', 'household__household_number', 'created_at']
    ordering          = ['-survey_year']

    def get_permissions(self):
        if self.action == 'destroy':
            # Hard-delete: SUPER_ADMIN only
            return [CanDeleteSurvey(), NotForcingPasswordChange()]
        if self.action in ('verify', 'request_revision'):
            return [IsAdmin(), NotForcingPasswordChange()]
        if self.action in ('create', 'partial_update', 'submit'):
            return [CanEncodeSurvey(), NotForcingPasswordChange()]
        return [CanViewSurvey(), NotForcingPasswordChange()]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSurveySerializer
        if self.action == 'partial_update':
            return SurveyDataUpdateSerializer
        if self.action == 'list':
            return HouseholdSurveyLightSerializer
        return HouseholdSurveySerializer

    def get_queryset(self):
        perm_flag = self._perm_flag_for_action()
        purok_ids = self._allowed_purok_ids(perm_flag)
        manager   = HouseholdSurvey.all_objects if self._include_deleted() else HouseholdSurvey.objects

        qs = (
            manager
            .select_related('household__purok', 'form_schema', 'surveyed_by', 'verified_by')
            .prefetch_related(
                Prefetch('families', queryset=Family.objects.prefetch_related(
                    Prefetch('persons', queryset=Person.objects.all()),
                    'programs_availed',
                )),
            )
        )
        if purok_ids is not None:
            qs = qs.filter(household__purok_id__in=purok_ids)
        return qs

    def create(self, request, *args, **kwargs):
        """POST /surveys/ — full nested create."""
        serializer = CreateSurveySerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        survey = serializer.save()
        return Response(HouseholdSurveySerializer(survey).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /surveys/{id}/ — update survey data JSON + metadata.

        Optimistic locking: if the client sends `updated_at` in the request body,
        the server checks it matches the current value. A mismatch means another
        user edited the record since the client last fetched it — returns 409.
        """
        survey = self.get_object()

        # Optimistic locking check
        client_updated_at = request.data.get('updated_at')
        if client_updated_at:
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(str(client_updated_at))
            if parsed and survey.updated_at and abs(
                (survey.updated_at.replace(tzinfo=None) if survey.updated_at.tzinfo else survey.updated_at)
                - (parsed.replace(tzinfo=None) if parsed.tzinfo else parsed)
            ).total_seconds() > 1:
                return Response(
                    {
                        'error': 'conflict',
                        'detail': (
                            'This record was modified by another user after you loaded it. '
                            'Please reload the page and re-apply your changes.'
                        ),
                        'server_updated_at': survey.updated_at,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        serializer = SurveyDataUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            if 'data' in data:
                survey = HouseholdService.update_survey_data(
                    survey=survey,
                    new_data=data['data'],
                    updated_by=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            update_fields = ['updated_by', 'updated_at']
            for field in ('surveyed_at', 'notes'):
                if field in data:
                    setattr(survey, field, data[field])
                    update_fields.append(field)
            survey.updated_by = request.user
            survey.save(update_fields=update_fields)
        except SurveyImmutableError as exc:
            raise ValidationError({'detail': str(exc)})

        return Response(HouseholdSurveySerializer(survey).data)

    def perform_destroy(self, instance):
        HouseholdService.soft_delete_survey(
            survey=instance,
            deleted_by=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )

    def _transition_action(self, request, action_name: str):
        survey = self.get_object()
        notes  = request.data.get('notes', '')
        ip     = request.META.get('REMOTE_ADDR')
        try:
            if action_name == 'submit':
                survey = HouseholdService.submit_survey(survey, submitted_by=request.user, ip_address=ip)
            elif action_name == 'verify':
                survey = HouseholdService.verify_survey(survey, verified_by=request.user, notes=notes, ip_address=ip)
            elif action_name == 'request_revision':
                if not notes:
                    raise ValidationError({'notes': 'Notes are required when requesting revision.'})
                survey = HouseholdService.request_revision(survey, requested_by=request.user, notes=notes, ip_address=ip)
        except InvalidStatusTransitionError as exc:
            raise ValidationError({'detail': str(exc)})
        return Response(HouseholdSurveySerializer(survey).data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """POST /surveys/{id}/submit/ — DRAFT|REVISION → SUBMITTED"""
        return self._transition_action(request, 'submit')

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """POST /surveys/{id}/verify/ — SUBMITTED → VERIFIED (ADMIN+)"""
        return self._transition_action(request, 'verify')

    @action(detail=True, methods=['post'], url_path='request-revision')
    def request_revision(self, request, pk=None):
        """POST /surveys/{id}/request-revision/ — SUBMITTED → REVISION (ADMIN+)"""
        return self._transition_action(request, 'request_revision')


# ─────────────────────────────────────────────────────────────────────────────
# FamilyViewSet
# ─────────────────────────────────────────────────────────────────────────────

class FamilyViewSet(PurokScopedMixin,
                    viewsets.mixins.ListModelMixin,
                    viewsets.mixins.RetrieveModelMixin,
                    viewsets.mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """
    Read + partial update for Family records.

    Filters:  ?household_survey={uuid}  ?income_bracket=5K_10K  ?survey_year=2024  ?purok=3
    Order:    ?ordering=family_number | survey_year | monthly_income_bracket
    """
    http_method_names = ['get', 'patch', 'head', 'options']
    permission_classes = [CanViewSurvey, NotForcingPasswordChange]
    pagination_class   = ProfilingPagination
    filterset_class    = FamilyFilter
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields    = ['family_number', 'monthly_income_bracket',
                          'household_survey__survey_year']
    ordering           = ['household_survey__survey_year', 'family_number']

    def get_permissions(self):
        if self.action == 'partial_update':
            return [CanEncodeSurvey(), NotForcingPasswordChange()]
        return [CanViewSurvey(), NotForcingPasswordChange()]

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return FamilyUpdateSerializer
        return FamilySerializer

    def get_queryset(self):
        perm_flag = self._perm_flag_for_action()
        purok_ids = self._allowed_purok_ids(perm_flag)

        qs = (
            Family.objects
            .select_related('household_survey__household__purok')
            .prefetch_related(
                Prefetch('persons', queryset=Person.objects.all()),
                'programs_availed',
            )
        )
        if purok_ids is not None:
            qs = qs.filter(household_survey__household__purok_id__in=purok_ids)
        return qs

    def partial_update(self, request, *args, **kwargs):
        family = self.get_object()
        serializer = FamilyUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            family = HouseholdService.update_family(
                family=family,
                updates=serializer.validated_data,
                updated_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except SurveyImmutableError as exc:
            raise ValidationError({'detail': str(exc)})
        return Response(FamilySerializer(family).data)


# ─────────────────────────────────────────────────────────────────────────────
# PersonViewSet
# ─────────────────────────────────────────────────────────────────────────────

class PersonViewSet(PurokScopedMixin,
                    viewsets.mixins.ListModelMixin,
                    viewsets.mixins.RetrieveModelMixin,
                    viewsets.mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """
    Read + partial update for Person records.

    Filters:  ?gender=FEMALE  ?sector=PWD  ?age_min=18&age_max=59
              ?educational_attainment=COLLEGE_GRAD  ?survey_year=2024
              ?civil_status=MARRIED  ?role=HEAD  ?purok=3
              ?is_registered_voter=true
    Search:   ?search=partial_name
    Order:    ?ordering=last_name | gender | age_at_survey | survey_year

    Demographic filter examples:
        /persons/?sector=PWD&survey_year=2024
        /persons/?gender=FEMALE&age_min=15&age_max=30&survey_year=2024
        /persons/?sectors=PWD,SENIOR&educational_attainment=NO_FORMAL
    """
    http_method_names = ['get', 'patch', 'head', 'options']
    pagination_class  = ProfilingPagination
    filterset_class   = PersonFilter
    filter_backends   = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields     = ['first_name', 'last_name', 'middle_name']
    ordering_fields   = [
        'last_name', 'first_name', 'gender', 'age_at_survey',
        'date_of_birth', 'educational_attainment',
        'family__household_survey__survey_year',
    ]
    ordering = ['last_name', 'first_name']

    def get_permissions(self):
        if self.action == 'partial_update':
            return [CanEncodeSurvey(), NotForcingPasswordChange()]
        return [CanViewSurvey(), NotForcingPasswordChange()]

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return PersonUpdateSerializer
        return PersonSerializer

    def get_queryset(self):
        perm_flag = self._perm_flag_for_action()
        purok_ids = self._allowed_purok_ids(perm_flag)

        qs = (
            Person.objects
            .select_related('family__household_survey__household__purok')
        )
        if purok_ids is not None:
            qs = qs.filter(
                family__household_survey__household__purok_id__in=purok_ids
            )
        return qs

    def partial_update(self, request, *args, **kwargs):
        # Re-fetch with select_related to avoid N+1 in log_change
        person = (
            Person.objects
            .select_related('family__household_survey__household')
            .get(pk=self.get_object().pk)
        )
        serializer = PersonUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            person = HouseholdService.update_person(
                person=person,
                updates=serializer.validated_data,
                updated_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except SurveyImmutableError as exc:
            raise ValidationError({'detail': str(exc)})
        return Response(PersonSerializer(person).data)


# ─────────────────────────────────────────────────────────────────────────────
# ProgramAvailedViewSet
# ─────────────────────────────────────────────────────────────────────────────

class ProgramAvailedViewSet(PurokScopedMixin, viewsets.ModelViewSet):
    """
    Full CRUD for ProgramAvailed records.

    Filters:  ?program_type=4PS  ?survey_year=2024  ?purok=3
              ?date_from=2024-01-01&date_to=2024-12-31  ?family={uuid}
    Order:    ?ordering=-date_availed | program_type
    """
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    pagination_class  = ProfilingPagination
    filterset_class   = ProgramAvailedFilter
    filter_backends   = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields     = ['program_name', 'reference_no']
    ordering_fields   = ['date_availed', 'program_type', 'amount']
    ordering          = ['-date_availed']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [CanViewSurvey(), NotForcingPasswordChange()]
        return [CanEncodeSurvey(), NotForcingPasswordChange()]

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return ProgramAvailedWriteSerializer
        return ProgramAvailedSerializer

    def get_queryset(self):
        perm_flag = self._perm_flag_for_action()
        purok_ids = self._allowed_purok_ids(perm_flag)

        qs = (
            ProgramAvailed.objects
            .select_related(
                'family__household_survey__household__purok',
                'beneficiary',
            )
        )
        if purok_ids is not None:
            qs = qs.filter(
                family__household_survey__household__purok_id__in=purok_ids
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete(deleted_by_user=self.request.user)


# ─────────────────────────────────────────────────────────────────────────────
# FormSchema / FieldMapping ViewSets
# ─────────────────────────────────────────────────────────────────────────────

class FormSchemaViewSet(viewsets.ModelViewSet):
    """
    GET  /schemas/       — list (staff+)
    POST /schemas/       — create (ADMIN+)
    PATCH /schemas/{id}/ — update (ADMIN+)

    Filters: ?year=2024  ?is_active=true
    Search:  ?search=name
    """
    pagination_class = ProfilingPagination
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['name', 'description']
    ordering_fields  = ['year', 'version', 'created_at']
    ordering         = ['-year', '-version']
    filterset_fields = ['year', 'is_active']

    def get_queryset(self):
        return FormSchema.objects.all()

    def get_serializer_class(self):
        return FormSchemaSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [CanViewSurvey(), NotForcingPasswordChange()]
        return [IsAdmin(), NotForcingPasswordChange()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class FieldMappingViewSet(viewsets.ModelViewSet):
    """
    GET  /mappings/       — list (staff+)
    POST /mappings/       — create (ADMIN+)
    PATCH /mappings/{id}/ — update (ADMIN+)

    Filters: ?level=household  ?data_type=select
    Search:  ?search=canonical_name_or_label
    """
    pagination_class = ProfilingPagination
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['canonical_name', 'label']
    ordering_fields  = ['canonical_name', 'level']
    ordering         = ['level', 'canonical_name']
    filterset_fields = ['level', 'data_type']

    def get_queryset(self):
        return FieldMapping.objects.all()

    def get_serializer_class(self):
        return FieldMappingSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [CanViewSurvey(), NotForcingPasswordChange()]
        return [IsAdmin(), NotForcingPasswordChange()]


# ─────────────────────────────────────────────────────────────────────────────
# QueryViewSet  (cross-year analytical queries)
# ─────────────────────────────────────────────────────────────────────────────

class QueryViewSet(viewsets.ViewSet):
    """
    Read-only analytical queries powered by NormalizedData and direct ORM.

    GET /query/filter-by-concept/  — find surveys matching a canonical concept+value
    GET /query/get-trend/          — year-over-year count for a concept+value
    GET /query/demographics/       — demographic summary for a year
    GET /query/concepts/           — list all available FieldMapping concepts
    GET /query/concept-values/     — unique values for one concept in a given year
    """
    permission_classes = [CanViewSurvey, NotForcingPasswordChange]

    def _purok_ids_from_request(self):
        raw = self.request.query_params.getlist('purok_ids')
        if raw:
            try:
                return [int(p) for p in raw]
            except ValueError:
                raise ValidationError({'purok_ids': 'Must be integers.'})
        return None

    @action(detail=False, methods=['get'], url_path='filter-by-concept')
    def filter_by_concept(self, request):
        """
        GET /query/filter-by-concept/
            ?canonical_name=water_source
            &canonical_value=level_3
            &year_start=2024
            &year_end=2026
            &level=household          (optional, default: household)
            &purok_ids=1&purok_ids=2  (optional)
            &page=1&page_size=20      (pagination)

        Finds all HouseholdSurveys where the concept has the given value,
        across the specified year range.

        Example: "All households with metered water (2024–2026)"
            /query/filter-by-concept/?canonical_name=water_source&canonical_value=level_3&year_start=2024&year_end=2026
        """
        canonical_name  = request.query_params.get('canonical_name')
        canonical_value = request.query_params.get('canonical_value')
        year_start      = request.query_params.get('year_start')
        year_end        = request.query_params.get('year_end')
        level           = request.query_params.get('level', 'household')

        errors = {}
        if not canonical_name:  errors['canonical_name']  = 'Required.'
        if not canonical_value: errors['canonical_value'] = 'Required.'
        if not year_start:      errors['year_start']      = 'Required.'
        if not year_end:        errors['year_end']        = 'Required.'
        if errors:
            raise ValidationError(errors)

        try:
            year_start, year_end = int(year_start), int(year_end)
        except ValueError:
            raise ValidationError({'year_start': 'Must be integers.'})

        qs = QueryService.filter_by_concept(
            canonical_name=canonical_name,
            canonical_value=canonical_value,
            year_start=year_start,
            year_end=year_end,
            level=level,
            purok_ids=self._purok_ids_from_request(),
        )

        paginator = ProfilingPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                HouseholdSurveyLightSerializer(page, many=True).data
            )
        return Response(HouseholdSurveyLightSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='get-trend')
    def get_trend(self, request):
        """
        GET /query/get-trend/
            ?canonical_name=water_source
            &canonical_value=level_3
            &years=2024,2025,2026
            &purok_ids=1  (optional)

        Returns year-over-year count of unique households matching the concept.

        Example: "How many households per year had metered water?"
        Response:
            {
              "canonical_name": "water_source",
              "canonical_value": "level_3",
              "trend": [
                {"year": 2024, "count": 45},
                {"year": 2025, "count": 67},
                {"year": 2026, "count": 89}
              ]
            }
        """
        canonical_name  = request.query_params.get('canonical_name')
        canonical_value = request.query_params.get('canonical_value')
        years_raw       = request.query_params.get('years', '')

        if not canonical_name or not canonical_value or not years_raw:
            raise ValidationError({'detail': 'canonical_name, canonical_value, and years are required.'})

        try:
            years = [int(y.strip()) for y in years_raw.split(',') if y.strip()]
        except ValueError:
            raise ValidationError({'years': 'Comma-separated integers, e.g. 2024,2025,2026'})

        trend = QueryService.get_trend(
            canonical_name=canonical_name,
            canonical_value=canonical_value,
            years=years,
            purok_ids=self._purok_ids_from_request(),
        )
        return Response({
            'canonical_name':  canonical_name,
            'canonical_value': canonical_value,
            'trend':           trend,
        })

    @action(detail=False, methods=['get'])
    def demographics(self, request):
        """
        GET /query/demographics/?survey_year=2024&purok_ids=1&purok_ids=2

        Returns demographic breakdown: totals, gender, age groups,
        civil status, education, sectors, income brackets.
        """
        year_raw = request.query_params.get('survey_year')
        if not year_raw:
            raise ValidationError({'survey_year': 'Required.'})
        try:
            survey_year = int(year_raw)
        except ValueError:
            raise ValidationError({'survey_year': 'Must be an integer.'})

        return Response(
            QueryService.get_demographics_summary(
                survey_year=survey_year,
                purok_ids=self._purok_ids_from_request(),
            )
        )

    @action(detail=False, methods=['get'])
    def concepts(self, request):
        """
        GET /query/concepts/
            ?level=household          filter by level (household|family|person)
            ?search=water             partial match on canonical_name or label
            ?data_type=select         filter by data type

        Lists all available FieldMapping concepts for building filter UIs.

        Response:
            [
              {
                "canonical_name": "water_source",
                "label": "Water Source",
                "level": "household",
                "data_type": "select",
                "canonical_options": [
                  {"value": "level_1", "label": "Nature/Spring"},
                  {"value": "level_3", "label": "Metered"}
                ],
                "years_covered": [2024, 2025, 2026]
              },
              ...
            ]
        """
        qs = FieldMapping.objects.all().order_by('level', 'canonical_name')

        level     = request.query_params.get('level')
        data_type = request.query_params.get('data_type')
        search    = request.query_params.get('search', '').strip()

        if level:
            qs = qs.filter(level=level)
        if data_type:
            qs = qs.filter(data_type=data_type)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(canonical_name__icontains=search) | Q(label__icontains=search)
            )

        result = []
        for fm in qs:
            result.append({
                'canonical_name':   fm.canonical_name,
                'label':            fm.label,
                'level':            fm.level,
                'data_type':        fm.data_type,
                'canonical_options': fm.canonical_options,
                'years_covered':    sorted(fm.year_map.keys()),
                'notes':            fm.notes,
            })
        return Response(result)

    @action(detail=False, methods=['get'], url_path='concept-values')
    def concept_values(self, request):
        """
        GET /query/concept-values/?canonical_name=water_source&year=2024&purok_ids=1

        Returns the distinct canonical_values recorded for a concept in a year.
        Used to populate filter dropdowns with only values that actually exist
        in the data (rather than all theoretical options from FieldMapping).

        Response:
            {
              "canonical_name": "water_source",
              "year": 2024,
              "values": [
                {"canonical_value": "level_1", "count": 120},
                {"canonical_value": "level_3", "count": 450}
              ]
            }
        """
        canonical_name = request.query_params.get('canonical_name')
        year_raw       = request.query_params.get('year')

        if not canonical_name:
            raise ValidationError({'canonical_name': 'Required.'})

        qs = NormalizedData.objects.filter(canonical_name=canonical_name)
        if year_raw:
            try:
                qs = qs.filter(survey_year=int(year_raw))
            except ValueError:
                raise ValidationError({'year': 'Must be an integer.'})

        purok_ids = self._purok_ids_from_request()
        if purok_ids:
            qs = qs.filter(
                household_survey__household__purok_id__in=purok_ids
            )

        values = (
            qs.values('canonical_value')
            .annotate(count=Count('household_survey', distinct=True))
            .order_by('-count')
        )
        return Response({
            'canonical_name': canonical_name,
            'year':           int(year_raw) if year_raw else None,
            'values':         list(values),
        })


# ─────────────────────────────────────────────────────────────────────────────
# ReportViewSet  (downloads)
# ─────────────────────────────────────────────────────────────────────────────

class ReportViewSet(viewsets.ViewSet):
    """
    Generates downloadable export files.

    GET /reports/export/
        ?entity_type=person|survey|household|family|program
        &format=csv|excel
        &survey_year=2024              (single year)
        &year_start=2022&year_end=2024 (year range)
        &purok_ids=1&purok_ids=2       (location filter)
        &status=VERIFIED               (survey status filter)
        &include_deleted=true          (ADMIN+ only)

    POST /reports/rebuild-normalized/
        Body: {"year": 2024}           (optional; omit to rebuild ALL)
        ADMIN+ only. Triggers full NormalizedData rebuild.

    PERMISSION: Staff need perm_generate_reports=True on their StaffProfile.
                ADMIN+ can always export.
    """
    permission_classes = [CanExportSurvey, NotForcingPasswordChange]

    def _check_export_permission(self):
        """
        Secondary check for StaffProfile.perm_generate_reports.
        CanExportSurvey (view-level) already gates via purok can_export flag.
        This additionally enforces the profile-level report generation toggle.
        """
        user = self.request.user
        if user.role in ('SUPER_ADMIN', 'ADMIN'):
            return
        profile = getattr(user, 'staff_profile', None)
        if not profile or not profile.perm_generate_reports:
            raise PermissionDenied(
                'You do not have permission to generate reports. '
                'Ask your administrator to enable perm_generate_reports.'
            )

    def _build_filters(self, request) -> dict:
        filters_dict = {}

        year = request.query_params.get('survey_year')
        if year:
            filters_dict['survey_year'] = int(year)

        year_start = request.query_params.get('year_start')
        year_end   = request.query_params.get('year_end')
        if year_start and year_end:
            filters_dict['survey_year'] = [int(year_start), int(year_end)]

        purok_ids = request.query_params.getlist('purok_ids')
        if purok_ids:
            filters_dict['purok_ids'] = [int(p) for p in purok_ids]

        survey_status = request.query_params.get('status')
        if survey_status:
            filters_dict['status'] = survey_status

        include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
        if include_deleted and request.user.role not in ('SUPER_ADMIN', 'ADMIN'):
            raise PermissionDenied('Only admins can export deleted records.')
        filters_dict['include_deleted'] = include_deleted

        return filters_dict

    @action(detail=False, methods=['get'])
    def export(self, request):
        """GET /reports/export/ — returns a downloadable file."""
        self._check_export_permission()

        entity_type = request.query_params.get('entity_type', 'survey')
        fmt         = request.query_params.get('format', 'csv').lower()

        try:
            result = ReportService.generate_export(
                entity_type=entity_type,
                filters=self._build_filters(request),
                fmt=fmt,
            )
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        except NotImplementedError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except ImportError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        response = HttpResponse(result.content, content_type=result.content_type)
        response['Content-Disposition'] = f'attachment; filename="{result.filename}"'
        return response

    @action(detail=False, methods=['post'], url_path='rebuild-normalized')
    def rebuild_normalized(self, request):
        """POST /reports/rebuild-normalized/ — trigger NormalizedData rebuild (ADMIN+)."""
        if request.user.role not in ('SUPER_ADMIN', 'ADMIN'):
            raise PermissionDenied('Only admins can trigger a NormalizedData rebuild.')

        year = request.data.get('year')
        if year is not None:
            try:
                year = int(year)
            except (TypeError, ValueError):
                raise ValidationError({'year': 'Must be an integer.'})

        return Response(NormalizationService.rebuild_all_normalized_data(year=year))
