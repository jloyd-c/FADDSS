from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FieldMappingViewSet,
    FormSchemaViewSet,
    FamilyViewSet,
    HouseholdSurveyViewSet,
    HouseholdViewSet,
    PersonViewSet,
    ProgramAvailedViewSet,
    QueryViewSet,
    ReportViewSet,
)

router = DefaultRouter()

# ── Core data hierarchy ──────────────────────────────────────────────────────
router.register(r'households', HouseholdViewSet,       basename='household')
router.register(r'surveys',    HouseholdSurveyViewSet, basename='survey')
router.register(r'families',   FamilyViewSet,          basename='family')
router.register(r'persons',    PersonViewSet,          basename='person')
router.register(r'programs',   ProgramAvailedViewSet,  basename='program')

# ── Schema & field mapping (admin-managed config) ────────────────────────────
router.register(r'schemas',  FormSchemaViewSet,   basename='schema')
router.register(r'mappings', FieldMappingViewSet, basename='mapping')

# ── Analytical queries (NormalizedData-backed) ───────────────────────────────
router.register(r'query',   QueryViewSet,  basename='query')
router.register(r'reports', ReportViewSet, basename='report')

# ── Generated URL patterns ───────────────────────────────────────────────────
# households/                             GET, POST
# households/{id}/                        GET, PATCH, DELETE
# households/{id}/surveys/                GET
# households/{id}/latest-survey/          GET
# households/{id}/compare/                GET  ?year_a=2024&year_b=2025
# households/{id}/change-log/             GET
#
# surveys/                                GET, POST  (nested create)
# surveys/{id}/                           GET, PATCH, DELETE
# surveys/{id}/submit/                    POST
# surveys/{id}/verify/                    POST
# surveys/{id}/request-revision/          POST
#
# families/                               GET
# families/{id}/                          GET, PATCH
#
# persons/                                GET  ?q=name&year=2024&sectors=PWD
# persons/{id}/                           GET, PATCH
#
# programs/                               GET, POST
# programs/{id}/                          GET, PATCH, DELETE
#
# schemas/                                GET, POST
# schemas/{id}/                           GET, PATCH
#
# mappings/                               GET, POST
# mappings/{id}/                          GET, PATCH
#
# query/filter-by-concept/                GET
# query/get-trend/                        GET
# query/demographics/                     GET
#
# reports/export/                         GET  (download)
# reports/rebuild-normalized/             POST (admin only)

urlpatterns = [
    path('', include(router.urls)),
]
