from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'action', 'target_user', 'ip_address')
    list_filter = ('action',)
    search_fields = ('actor__email', 'target_user__email', 'ip_address')
    readonly_fields = ('timestamp', 'actor', 'action', 'target_user', 'ip_address', 'user_agent', 'extra')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
