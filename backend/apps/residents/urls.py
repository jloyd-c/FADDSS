from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurokViewSet, ResidentViewSet

router = DefaultRouter()
router.register(r'puroks', PurokViewSet, basename='purok')
router.register(r'residents', ResidentViewSet, basename='resident')

urlpatterns = [
    path('', include(router.urls)),
]
