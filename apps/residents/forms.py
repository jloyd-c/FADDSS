from django import forms
from .models import Resident
from .models import Household


class ResidentForm(forms.ModelForm):
    """Form for creating and updating residents"""
    
    class Meta:
        model = Resident
        fields = [
            'first_name', 'middle_name', 'last_name', 'suffix',
            'date_of_birth', 'gender', 'civil_status',
            'phone_number', 'email',
            'purok', 'street',
            'is_pwd', 'is_senior', 'is_4ps',
            'employment_status', 'occupation',
            'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reyes'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dela Cruz'}),
            'suffix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jr., Sr., III (optional)'}),
            
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'civil_status': forms.Select(attrs={'class': 'form-select'}),
            
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09171234567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'juan@example.com'}),
            
            'purok': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rizal Street'}),
            
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Teacher, Farmer'}),
            
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
        }
        labels = {
            'is_pwd': 'Person with Disability (PWD)',
            'is_senior': 'Senior Citizen (60+)',
            'is_4ps': '4Ps Beneficiary',
        }


class HouseholdForm(forms.ModelForm):
    """Form for creating and updating households"""
    
    class Meta:
        model = Household
        fields = [
            'street', 'purok',
            'housing_type', 'housing_condition',
            'has_electricity', 'has_water', 'water_source',
            'monthly_income',
            'notes'
        ]
        widgets = {
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rizal Street'}),
            'purok': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            
            'housing_type': forms.Select(attrs={'class': 'form-select'}),
            'housing_condition': forms.Select(attrs={'class': 'form-select'}),
            
            'water_source': forms.Select(attrs={'class': 'form-select'}),
            
            'monthly_income': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '10000.00',
                'step': '0.01'
            }),
            
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
        }


class HouseholdMemberForm(forms.ModelForm):
    """Form for assigning residents to household"""
    
    class Meta:
        model = Resident
        fields = ['household', 'relationship_to_head']
        widgets = {
            'household': forms.Select(attrs={'class': 'form-select'}),
            'relationship_to_head': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Spouse, Child, Parent, Sibling'
            }),
        }