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
    message = {'detail': 'Only Super Admins can perform this action.'}

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'SUPER_ADMIN')


class IsAdmin(BasePermission):
    """Allows SUPER_ADMIN and ADMIN roles."""
    message = {'detail': 'Only Admins can perform this action.'}

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

    View-level (coarse gate):
      - SUPER_ADMIN and ADMIN: always pass
      - STAFF: must have can_create=True OR can_edit=True on at least one purok

    Object-level (fine-grained, called via has_object_permission):
      - SUPER_ADMIN and ADMIN: always pass
      - STAFF: must have can_create|can_edit on the SPECIFIC purok of the object

    The object passed must expose a `get_purok_id()` method or a
    `household.purok_id` / `purok_id` attribute.
    """
    message = {'detail': 'You do not have encode permission for this purok.'}

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

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if request.user.role == 'STAFF':
            purok_id = _get_purok_id(obj)
            if purok_id is None:
                return True  # Can't determine purok — fall back to view-level check
            from django.db.models import Q
            return request.user.purok_permissions.filter(
                purok_id=purok_id,
            ).filter(
                Q(can_create=True) | Q(can_edit=True)
            ).exists()
        return False


class CanViewSurvey(BasePermission):
    """
    Viewer role: read-only access to survey data.

    View-level: ADMIN+ always; STAFF with can_view on any purok; RESIDENT with
    a linked Person (checked at object level).

    Object-level:
      - ADMIN+: always
      - STAFF: can_view=True on the specific purok
      - RESIDENT: object belongs to their household
    """
    message = {'detail': 'You do not have view permission for this purok.'}

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if request.user.role == 'STAFF':
            return request.user.purok_permissions.filter(can_view=True).exists()
        if request.user.role == 'RESIDENT':
            # Coarse gate: resident must have a linked person
            return request.user.person_id is not None
        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if request.user.role == 'STAFF':
            purok_id = _get_purok_id(obj)
            if purok_id is None:
                return True
            return request.user.purok_permissions.filter(
                purok_id=purok_id, can_view=True
            ).exists()
        if request.user.role == 'RESIDENT':
            return _resident_owns_object(request.user, obj)
        return False


class CanExportSurvey(BasePermission):
    """
    Export permission: download CSV/Excel reports.

    - SUPER_ADMIN, ADMIN: always allowed
    - STAFF: needs can_export=True on the specific purok(s) requested
      (queryset-level filtering further restricts to permitted puroks)
    """
    message = {'detail': 'You do not have export permission for the requested puroks.'}

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if request.user.role == 'STAFF':
            return request.user.purok_permissions.filter(can_export=True).exists()
        return False


class CanDeleteSurvey(BasePermission):
    """
    Hard-delete permission for survey records.
    Only SUPER_ADMIN may delete surveys — ADMIN and STAFF cannot.
    """
    message = {'detail': 'Only Super Admins can delete survey records.'}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'SUPER_ADMIN'
        )


class CanViewAuditLogs(BasePermission):
    """
    Audit log access:
      - SUPER_ADMIN, ADMIN: full access (no filtering)
      - STAFF: access only if they have can_view_audit_logs=True on at least one purok
               (queryset-level filtering restricts to those puroks + excludes NULL-purok logs)
      - RESIDENT: no access
    """
    message = {'detail': 'You do not have permission to view audit logs.'}

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if request.user.role == 'STAFF':
            return request.user.purok_permissions.filter(can_view_audit_logs=True).exists()
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_purok_id(obj) -> int | None:
    """
    Extract the purok_id from a profiling model instance.
    Supports Household, HouseholdSurvey, Family, Person, ProgramAvailed.
    Returns None if the purok cannot be determined.
    """
    # Direct purok FK (Household)
    if hasattr(obj, 'purok_id') and obj.purok_id:
        return obj.purok_id
    # Via household (HouseholdSurvey)
    if hasattr(obj, 'household_id'):
        try:
            return obj.household.purok_id
        except Exception:
            pass
    # Via household_survey.household (Family)
    if hasattr(obj, 'household_survey_id'):
        try:
            return obj.household_survey.household.purok_id
        except Exception:
            pass
    # Via family.household_survey.household (Person, ProgramAvailed)
    if hasattr(obj, 'family_id'):
        try:
            return obj.family.household_survey.household.purok_id
        except Exception:
            pass
    return None


def _resident_owns_object(user, obj) -> bool:
    """
    Returns True if the RESIDENT user's linked Person belongs to the
    household/survey represented by obj.
    """
    if not user.person_id:
        return False
    try:
        # Get the household_id that the resident's person belongs to
        person = user.person
        household_survey = person.family.household_survey
        household_id = household_survey.household_id

        # Check the object
        if hasattr(obj, 'id') and hasattr(obj, 'purok_id'):
            # obj is a Household
            return str(obj.id) == str(household_id)
        if hasattr(obj, 'household_id'):
            # obj is a HouseholdSurvey
            return str(obj.household_id) == str(household_id)
        if hasattr(obj, 'household_survey_id'):
            # obj is a Family — check its survey's household
            return str(obj.household_survey.household_id) == str(household_id)
        if hasattr(obj, 'family_id'):
            # obj is a Person or ProgramAvailed
            return str(obj.family.household_survey.household_id) == str(household_id)
    except Exception:
        pass
    return False
