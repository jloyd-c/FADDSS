from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUserViewSet, StaffUserViewSet, UserProfileView

router = DefaultRouter()
router.register('admins', AdminUserViewSet, basename='admin-users')
router.register('staff', StaffUserViewSet, basename='staff-users')

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('', include(router.urls)),
]
