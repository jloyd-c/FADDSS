from django.urls import path
from . import views

app_name = 'residents'

urlpatterns = [
    # Resident URLs
    path('', views.ResidentListView.as_view(), name='list'),
    path('create/', views.ResidentCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ResidentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ResidentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ResidentDeleteView.as_view(), name='delete'),
    
    # Household URLs
    path('households/', views.HouseholdListView.as_view(), name='household_list'),
    path('households/create/', views.HouseholdCreateView.as_view(), name='household_create'),
    path('households/<int:pk>/', views.HouseholdDetailView.as_view(), name='household_detail'),
    path('households/<int:pk>/edit/', views.HouseholdUpdateView.as_view(), name='household_edit'),
    path('households/<int:pk>/delete/', views.HouseholdDeleteView.as_view(), name='household_delete'),
]