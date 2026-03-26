from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HouseholdViewSet, FamilyMemberViewSet, PersonalProfileViewSet

router = DefaultRouter()
router.register(r'households', HouseholdViewSet, basename='household')
router.register(r'family-members', FamilyMemberViewSet, basename='family-member')
router.register(r'personal-profiles', PersonalProfileViewSet, basename='personal-profile')

urlpatterns = [
    path('', include(router.urls)),
]
