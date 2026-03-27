from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUserViewSet, ResidentAccountView, StaffUserViewSet, UserProfileView

router = DefaultRouter()
router.register('admins', AdminUserViewSet, basename='admin-users')
router.register('staff', StaffUserViewSet, basename='staff-users')

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('residents/', ResidentAccountView.as_view(), name='resident-account-create'),
    path('', include(router.urls)),
]
