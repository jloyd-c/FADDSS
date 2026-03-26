from django.contrib import admin
from .models import Resident


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ('resident_id', 'user', 'status', 'contact_number', 'created_at')
    list_filter = ('status',)
    search_fields = ('resident_id', 'user__email', 'user__first_name', 'user__last_name')
