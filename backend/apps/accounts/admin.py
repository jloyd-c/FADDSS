from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from .models import StaffProfile, StaffPurokPermission, User


# Only SUPER_ADMIN accounts may access the Django admin panel.
def _super_admin_only(self, request):
    return (
        request.user.is_active
        and request.user.is_authenticated
        and getattr(request.user, 'role', None) == User.Role.SUPER_ADMIN
    )


admin.site.__class__.has_permission = _super_admin_only


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'phone', 'work_start', 'work_end')
    list_filter = ('department', 'allow_weekend', 'allow_after_hours')


@admin.register(StaffPurokPermission)
class StaffPurokPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'purok', 'can_view', 'can_create', 'can_edit', 'can_delete', 'can_export')
    list_filter = ('purok',)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.role == User.Role.SUPER_ADMIN:
            return False
        return super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        protected = queryset.filter(role=User.Role.SUPER_ADMIN)
        if protected.exists():
            messages.error(request, 'Super Admin accounts cannot be deleted.')
            queryset = queryset.exclude(role=User.Role.SUPER_ADMIN)
        super().delete_queryset(request, queryset)
