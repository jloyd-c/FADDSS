from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View
from apps.accounts.models import User
from apps.residents.models import Resident, Household


class AdminLoginView(LoginView):
    """Login view for admin portal"""
    template_name = 'admin_portal/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('admin_portal:dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Admin Login'
        return context


class AdminLogoutView(View):
    """Logout view for admin portal - accepts both GET and POST"""
    
    def get(self, request):
        logout(request)
        return redirect('admin_portal:login')
    
    def post(self, request):
        logout(request)
        return redirect('admin_portal:login')


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard for admin portal"""
    template_name = 'admin_portal/dashboard.html'
    login_url = reverse_lazy('admin_portal:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard'
        
        # Get statistics (we'll add real data later)
        context['total_residents'] = Resident.objects.filter(is_active=True).count()
        context['total_households'] = Household.objects.filter(is_active=True).count()
        context['total_programs'] = 0
        context['active_users'] = User.objects.filter(is_active=True).count()
        
        return context