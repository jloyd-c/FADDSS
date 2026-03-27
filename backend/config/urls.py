from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/users/', include('apps.accounts.urls')),
    path('api/v1/residents/', include('apps.residents.urls')),
    path('api/v1/profiling/', include('apps.profiling.urls')),
]
