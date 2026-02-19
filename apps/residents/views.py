from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from .models import Resident, Household
from .forms import ResidentForm, HouseholdForm, HouseholdMemberForm


class ResidentListView(LoginRequiredMixin, ListView):
    """List all residents with search and filter"""
    model = Resident
    template_name = 'residents/resident_list.html'
    context_object_name = 'residents'
    paginate_by = 20
    login_url = reverse_lazy('admin_portal:login')
    
    def get_queryset(self):
        queryset = Resident.objects.filter(is_active=True).order_by('-created_at')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(resident_id__icontains=search) |
                Q(phone_number__icontains=search)
            )
        
        # Filter by purok
        purok = self.request.GET.get('purok')
        if purok:
            queryset = queryset.filter(purok=purok)
        
        # Filter by gender
        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_residents'] = Resident.objects.filter(is_active=True).count()
        
        # Get unique puroks for filter dropdown
        context['puroks'] = Resident.objects.filter(
            is_active=True
        ).values_list('purok', flat=True).distinct().order_by('purok')
        
        # Preserve search parameters
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_purok'] = self.request.GET.get('purok', '')
        context['selected_gender'] = self.request.GET.get('gender', '')
        
        return context


class ResidentDetailView(LoginRequiredMixin, DetailView):
    """View detailed information about a resident"""
    model = Resident
    template_name = 'residents/resident_detail.html'
    context_object_name = 'resident'
    login_url = reverse_lazy('admin_portal:login')


class ResidentCreateView(LoginRequiredMixin, CreateView):
    """Create a new resident"""
    model = Resident
    form_class = ResidentForm
    template_name = 'residents/resident_form.html'
    success_url = reverse_lazy('residents:list')
    login_url = reverse_lazy('admin_portal:login')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Resident {form.instance.get_full_name()} added successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Resident'
        context['button_text'] = 'Add Resident'
        return context


class ResidentUpdateView(LoginRequiredMixin, UpdateView):
    """Update resident information"""
    model = Resident
    form_class = ResidentForm
    template_name = 'residents/resident_form.html'
    success_url = reverse_lazy('residents:list')
    login_url = reverse_lazy('admin_portal:login')
    
    def form_valid(self, form):
        messages.success(self.request, f'Resident {form.instance.get_full_name()} updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Resident'
        context['button_text'] = 'Update Resident'
        return context


class ResidentDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete a resident (mark as inactive)"""
    model = Resident
    template_name = 'residents/resident_confirm_delete.html'
    success_url = reverse_lazy('residents:list')
    login_url = reverse_lazy('admin_portal:login')
    
    def delete(self, request, *args, **kwargs):
        """Soft delete - mark as inactive instead of deleting"""
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Resident {self.object.get_full_name()} has been deactivated.')
        return super().delete(request, *args, **kwargs)

class HouseholdListView(LoginRequiredMixin, ListView):
    """List all households with search and filter"""
    model = Household
    template_name = 'residents/household_list.html'
    context_object_name = 'households'
    paginate_by = 20
    login_url = reverse_lazy('admin_portal:login')
    
    def get_queryset(self):
        queryset = Household.objects.filter(is_active=True).select_related('household_head').order_by('-created_at')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(household_id__icontains=search) |
                Q(street__icontains=search) |
                Q(household_head__first_name__icontains=search) |
                Q(household_head__last_name__icontains=search)
            )
        
        # Filter by purok
        purok = self.request.GET.get('purok')
        if purok:
            queryset = queryset.filter(purok=purok)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_households'] = Household.objects.filter(is_active=True).count()
        
        # Get unique puroks
        context['puroks'] = Household.objects.filter(
            is_active=True
        ).values_list('purok', flat=True).distinct().order_by('purok')
        
        # Preserve search parameters
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_purok'] = self.request.GET.get('purok', '')
        
        return context


class HouseholdDetailView(LoginRequiredMixin, DetailView):
    """View detailed information about a household"""
    model = Household
    template_name = 'residents/household_detail.html'
    context_object_name = 'household'
    login_url = reverse_lazy('admin_portal:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all members of this household
        context['members'] = self.object.members.filter(is_active=True)
        # Get available residents (not in any household)
        context['available_residents'] = Resident.objects.filter(
            is_active=True,
            household__isnull=True
        )
        return context


class HouseholdCreateView(LoginRequiredMixin, CreateView):
    """Create a new household"""
    model = Household
    form_class = HouseholdForm
    template_name = 'residents/household_form.html'
    success_url = reverse_lazy('residents:household_list')
    login_url = reverse_lazy('admin_portal:login')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Household {form.instance.household_id} created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Household'
        context['button_text'] = 'Create Household'
        return context


class HouseholdUpdateView(LoginRequiredMixin, UpdateView):
    """Update household information"""
    model = Household
    form_class = HouseholdForm
    template_name = 'residents/household_form.html'
    success_url = reverse_lazy('residents:household_list')
    login_url = reverse_lazy('admin_portal:login')
    
    def form_valid(self, form):
        messages.success(self.request, f'Household {form.instance.household_id} updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Household'
        context['button_text'] = 'Update Household'
        return context
    
    def get_success_url(self):
        return reverse_lazy('residents:household_detail', kwargs={'pk': self.object.pk})


class HouseholdDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete a household"""
    model = Household
    template_name = 'residents/household_confirm_delete.html'
    success_url = reverse_lazy('residents:household_list')
    login_url = reverse_lazy('admin_portal:login')
    
    def delete(self, request, *args, **kwargs):
        """Soft delete - mark as inactive"""
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Household {self.object.household_id} has been deactivated.')
        return super().delete(request, *args, **kwargs)