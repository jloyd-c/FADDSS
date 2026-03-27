from rest_framework.permissions import BasePermission

# URL names that remain accessible when must_change_password=True.
_MUST_CHANGE_EXEMPT_NAMES = {
    'auth-login',
    'auth-logout',
    'auth-refresh',
    'auth-me',
    'auth-change-password',
    'auth-2fa-setup',
    'auth-2fa-verify',
    'auth-verify-email',
}


class NotForcingPasswordChange(BasePermission):
    """
    Blocks API access (403) for users whose must_change_password=True,
    except for explicitly exempt endpoints.

    Views can also opt out by setting class attribute:
        allow_must_change_password = True
    """

    message = {
        'error': 'password_change_required',
        'detail': 'You must change your password before accessing this resource.',
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if not request.user.must_change_password:
            return True
        # View-level opt-out
        if getattr(view, 'allow_must_change_password', False):
            return True
        # URL-name based exemption
        from django.urls import resolve, Resolver404
        try:
            return resolve(request.path).url_name in _MUST_CHANGE_EXEMPT_NAMES
        except Resolver404:
            return False


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'SUPER_ADMIN')


class IsAdmin(BasePermission):
    """Allows SUPER_ADMIN and ADMIN roles."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN')
        )


class IsStaff(BasePermission):
    """Allows SUPER_ADMIN, ADMIN, and STAFF roles."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN', 'STAFF')
        )


class IsResident(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'RESIDENT')


class CanManageResidents(BasePermission):
    """
    - SUPER_ADMIN: always allowed
    - ADMIN with perm_manage_residents: always allowed
    - STAFF: allowed if they have at least one purok assignment
      (queryset-level filtering enforces the purok restriction)
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role == 'SUPER_ADMIN':
            return True
        if request.user.role == 'ADMIN' and request.user.perm_manage_residents:
            return True
        if request.user.role == 'STAFF':
            return request.user.purok_permissions.exists()
        return False


class CanManageStaff(BasePermission):
    """SUPER_ADMIN always allowed; ADMIN only if perm_manage_staff=True."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role == 'SUPER_ADMIN':
            return True
        return request.user.role == 'ADMIN' and request.user.perm_manage_staff


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        return hasattr(obj, 'user') and obj.user == request.user


# ── Profiling-specific role permissions ──────────────────────────────────────

class CanEncodeSurvey(BasePermission):
    """
    Encoder role: can create and edit survey data.

    Allowed:
      - SUPER_ADMIN and ADMIN always
      - STAFF who have can_create=True OR can_edit=True on at least one purok
        (queryset-level filtering in the ViewSet enforces the per-purok scope)

    Rationale: The permission check here is a fast global gate — it rejects
    users with zero create/edit permissions across ALL puroks without hitting
    the queryset. The purok-level scoping is enforced separately in get_queryset().
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if request.user.role == 'STAFF':
            from django.db.models import Q
            return request.user.purok_permissions.filter(
                Q(can_create=True) | Q(can_edit=True)
            ).exists()
        return False


class CanViewSurvey(BasePermission):
    """
    Viewer role: read-only access to survey data.

    Allowed:
      - SUPER_ADMIN and ADMIN always
      - STAFF who have can_view=True on at least one purok
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if request.user.role == 'STAFF':
            return request.user.purok_permissions.filter(can_view=True).exists()
        return False


class CanAccessDeletedRecords(BasePermission):
    """
    Allows SUPER_ADMIN and ADMIN to access soft-deleted records via
    `?include_deleted=true` on export/query endpoints.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN')
        )
