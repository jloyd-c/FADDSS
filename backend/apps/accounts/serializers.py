from django.db import transaction
from rest_framework import serializers

from apps.common.utils import generate_temp_password
from apps.residents.models import Purok
from .models import StaffProfile, StaffPurokPermission, User


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    """
    Base user representation — used in list views and as the
    `user` field in login/me responses.
    """
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'date_joined',
            'must_change_password',
            'perm_manage_residents', 'perm_manage_staff', 'perm_view_reports',
            'perm_delete_users', 'perm_change_system_settings',
            'person',          # nullable — only populated for RESIDENT
        )
        read_only_fields = ('id', 'date_joined', 'person')


class StaffPurokPermissionSerializer(serializers.ModelSerializer):
    purok_number = serializers.IntegerField(source='purok.number', read_only=True)
    purok_name   = serializers.CharField(source='purok.name',   read_only=True)

    class Meta:
        model  = StaffPurokPermission
        fields = (
            'id', 'purok', 'purok_number', 'purok_name',
            'can_view', 'can_create', 'can_edit', 'can_delete',
            'can_export', 'can_view_audit_logs',
        )
        read_only_fields = ('id', 'purok_number', 'purok_name')


class MeSerializer(serializers.ModelSerializer):
    """
    Rich representation for the authenticated user — returned in
    login responses and GET /auth/me/.

    For STAFF: includes the full assigned_puroks list so the
    frontend can build dynamic dropdowns and show/hide buttons
    without extra API calls.

    For ADMIN/SUPER_ADMIN: omits assigned_puroks (they have global access).
    """
    full_name       = serializers.ReadOnlyField()
    assigned_puroks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'date_joined',
            'must_change_password', 'require_2fa',
            'perm_manage_residents', 'perm_manage_staff', 'perm_view_reports',
            'perm_delete_users', 'perm_change_system_settings',
            'person',
            'assigned_puroks',
        )
        read_only_fields = fields

    def get_assigned_puroks(self, user):
        """
        Returns the full purok permission list for STAFF.
        Returns an empty list for ADMIN, SUPER_ADMIN, and RESIDENT
        (they either have global access or no purok-based access).
        """
        if user.role != 'STAFF':
            return []
        perms = (
            user.purok_permissions
            .select_related('purok')
            .order_by('purok__number')
        )
        return [
            {
                'purok_id':           p.purok_id,
                'purok_name':         p.purok.name,
                'purok_number':       p.purok.number,
                'can_view':           p.can_view,
                'can_create':         p.can_create,
                'can_edit':           p.can_edit,
                'can_delete':         p.can_delete,
                'can_export':         p.can_export,
                'can_view_audit_logs': p.can_view_audit_logs,
            }
            for p in perms
        ]


# ---------------------------------------------------------------------------
# Admin account
# ---------------------------------------------------------------------------

class CreateAdminSerializer(serializers.ModelSerializer):
    """Used by Super Admin to create an Admin account."""

    temp_password = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'first_name',
            'last_name',
            'email',
            'username',
            'require_2fa',
            'perm_manage_residents',
            'perm_manage_staff',
            'perm_view_reports',
            'perm_delete_users',
            'perm_change_system_settings',
            'temp_password',
        )
        read_only_fields = ('id', 'temp_password')

    def validate(self, attrs):
        # Prevent any API path from creating a SUPER_ADMIN.
        if attrs.get('role') == User.Role.SUPER_ADMIN:
            raise serializers.ValidationError(
                'Super Admin accounts can only be created via the command line.'
            )
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def create(self, validated_data):
        from django.utils import timezone
        from apps.accounts.models import EmailVerification
        from apps.audit.models import AuditLog
        from apps.audit.utils import log_action

        temp_password = generate_temp_password()
        request = self.context['request']

        user = User(
            **validated_data,
            role=User.Role.ADMIN,
            is_staff=True,
            must_change_password=True,
            email_verified=False,
            created_by=request.user,
        )
        user.set_password(temp_password)
        user.save()

        EmailVerification.objects.create(
            user=user,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )

        log_action(
            AuditLog.Action.ADMIN_CREATED,
            actor=request.user,
            request=request,
            target_user=user,
            extra={'email': user.email, 'username': user.username},
        )

        user.temp_password = temp_password
        return user


class AdminDetailSerializer(serializers.ModelSerializer):
    """
    Read/update view for an Admin account.

    Privilege escalation safeguards:
      - role is always read_only — cannot be changed via API
      - perm_delete_users can only be set by SUPER_ADMIN (validated below)
      - An admin cannot edit their own account through this endpoint
    """

    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    full_name        = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            'id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'username',
            'role',
            'is_active',
            'must_change_password',
            'require_2fa',
            'perm_manage_residents',
            'perm_manage_staff',
            'perm_view_reports',
            'perm_delete_users',
            'perm_change_system_settings',
            'created_by_email',
            'date_joined',
        )
        read_only_fields = ('id', 'role', 'created_by_email', 'date_joined', 'email')

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs

        # Only SUPER_ADMIN can grant perm_delete_users
        if 'perm_delete_users' in attrs and attrs['perm_delete_users']:
            if request.user.role != 'SUPER_ADMIN':
                raise serializers.ValidationError(
                    {'perm_delete_users': 'Only Super Admins can grant the delete permission.'}
                )

        # Only SUPER_ADMIN can grant perm_change_system_settings
        if 'perm_change_system_settings' in attrs and attrs['perm_change_system_settings']:
            if request.user.role != 'SUPER_ADMIN':
                raise serializers.ValidationError(
                    {'perm_change_system_settings': 'Only Super Admins can grant system settings permission.'}
                )

        return attrs


# ---------------------------------------------------------------------------
# Staff account
# ---------------------------------------------------------------------------

class StaffProfileSerializer(serializers.ModelSerializer):
    department_display = serializers.CharField(source='get_department_display', read_only=True)

    class Meta:
        model = StaffProfile
        fields = (
            'phone',
            'department',
            'department_display',
            'work_start',
            'work_end',
            'allow_weekend',
            'allow_after_hours',
            'perm_generate_reports',
        )


class _PurokPermissionInputSerializer(serializers.Serializer):
    """Nested input only — used inside CreateStaffSerializer."""
    purok               = serializers.PrimaryKeyRelatedField(queryset=Purok.objects.all())
    can_view            = serializers.BooleanField(default=True)
    can_create          = serializers.BooleanField(default=False)
    can_edit            = serializers.BooleanField(default=False)
    can_delete          = serializers.BooleanField(default=False)
    can_export          = serializers.BooleanField(default=False)
    can_view_audit_logs = serializers.BooleanField(default=False)


class CreateStaffSerializer(serializers.Serializer):
    """Used by Admin/Super Admin to create a Staff account in one request."""

    # User fields
    first_name = serializers.CharField(max_length=150)
    last_name  = serializers.CharField(max_length=150)
    email      = serializers.EmailField()
    username   = serializers.CharField(max_length=150, required=False, allow_blank=True)

    # StaffProfile fields
    phone              = serializers.CharField(max_length=15, required=False, allow_blank=True, default='')
    department         = serializers.ChoiceField(
        choices=StaffProfile.Department.choices, required=False, allow_blank=True, default=''
    )
    work_start         = serializers.TimeField(default='08:00:00')
    work_end           = serializers.TimeField(default='17:00:00')
    allow_weekend      = serializers.BooleanField(default=False)
    allow_after_hours  = serializers.BooleanField(default=False)
    perm_generate_reports = serializers.BooleanField(default=False)

    # Purok assignments
    purok_permissions = _PurokPermissionInputSerializer(many=True, required=False, default=list)

    # Read-only response fields
    id            = serializers.IntegerField(read_only=True)
    temp_password = serializers.CharField(read_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def create(self, validated_data):
        purok_permissions_data = validated_data.pop('purok_permissions', [])
        profile_fields = {
            'phone':               validated_data.pop('phone', ''),
            'department':          validated_data.pop('department', ''),
            'work_start':          validated_data.pop('work_start'),
            'work_end':            validated_data.pop('work_end'),
            'allow_weekend':       validated_data.pop('allow_weekend', False),
            'allow_after_hours':   validated_data.pop('allow_after_hours', False),
            'perm_generate_reports': validated_data.pop('perm_generate_reports', False),
        }

        temp_password = generate_temp_password()

        from apps.audit.models import AuditLog
        from apps.audit.utils import log_action

        request = self.context['request']

        with transaction.atomic():
            user = User(
                **validated_data,
                role=User.Role.STAFF,
                is_staff=False,
                email_verified=True,
                must_change_password=True,
                created_by=request.user,
            )
            user.set_password(temp_password)
            user.save()

            StaffProfile.objects.create(user=user, **profile_fields)

            StaffPurokPermission.objects.bulk_create([
                StaffPurokPermission(
                    user=user,
                    purok=perm['purok'],
                    can_view=perm.get('can_view', True),
                    can_create=perm.get('can_create', False),
                    can_edit=perm.get('can_edit', False),
                    can_delete=perm.get('can_delete', False),
                    can_export=perm.get('can_export', False),
                    can_view_audit_logs=perm.get('can_view_audit_logs', False),
                )
                for perm in purok_permissions_data
            ])

        log_action(
            AuditLog.Action.STAFF_CREATED,
            actor=request.user,
            request=request,
            target_user=user,
            extra={
                'email':            user.email,
                'department':       profile_fields.get('department', ''),
                'puroks_assigned':  [p['purok'].number for p in purok_permissions_data],
            },
        )

        user.temp_password = temp_password
        return user


class StaffDetailSerializer(serializers.ModelSerializer):
    """Read/update view for a Staff account, including profile and purok permissions."""

    full_name        = serializers.ReadOnlyField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    staff_profile    = StaffProfileSerializer(read_only=True)
    purok_permissions = StaffPurokPermissionSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'username',
            'role',
            'is_active',
            'must_change_password',
            'require_2fa',
            'created_by_email',
            'date_joined',
            'staff_profile',
            'purok_permissions',
        )
        read_only_fields = ('id', 'role', 'email', 'created_by_email', 'date_joined')


# ---------------------------------------------------------------------------
# Staff update (profile + purok permissions)
# ---------------------------------------------------------------------------

class UpdateStaffSerializer(serializers.ModelSerializer):
    """
    PATCH endpoint for Staff — updates user fields, StaffProfile fields,
    and replaces purok permissions in one request.
    """

    phone                 = serializers.CharField(max_length=15, required=False, allow_blank=True)
    department            = serializers.ChoiceField(choices=StaffProfile.Department.choices, required=False, allow_blank=True)
    work_start            = serializers.TimeField(required=False)
    work_end              = serializers.TimeField(required=False)
    allow_weekend         = serializers.BooleanField(required=False)
    allow_after_hours     = serializers.BooleanField(required=False)
    perm_generate_reports = serializers.BooleanField(required=False)
    purok_permissions     = _PurokPermissionInputSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'is_active',
            'phone', 'department', 'work_start', 'work_end',
            'allow_weekend', 'allow_after_hours', 'perm_generate_reports',
            'purok_permissions',
        )

    _PROFILE_FIELDS = {
        'phone', 'department', 'work_start', 'work_end',
        'allow_weekend', 'allow_after_hours', 'perm_generate_reports',
    }

    def update(self, instance, validated_data):
        from apps.audit.models import AuditLog
        from apps.audit.utils import log_action

        profile_data          = {k: validated_data.pop(k) for k in list(validated_data) if k in self._PROFILE_FIELDS}
        purok_permissions_data = validated_data.pop('purok_permissions', None)
        request               = self.context.get('request')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            StaffProfile.objects.update_or_create(user=instance, defaults=profile_data)

        if purok_permissions_data is not None:
            # Log permission change before replacing
            old_puroks = list(
                StaffPurokPermission.objects
                .filter(user=instance)
                .values('purok__number', 'can_view', 'can_create', 'can_edit',
                        'can_delete', 'can_export', 'can_view_audit_logs')
            )
            StaffPurokPermission.objects.filter(user=instance).delete()
            StaffPurokPermission.objects.bulk_create([
                StaffPurokPermission(
                    user=instance,
                    purok=perm['purok'],
                    can_view=perm.get('can_view', True),
                    can_create=perm.get('can_create', False),
                    can_edit=perm.get('can_edit', False),
                    can_delete=perm.get('can_delete', False),
                    can_export=perm.get('can_export', False),
                    can_view_audit_logs=perm.get('can_view_audit_logs', False),
                )
                for perm in purok_permissions_data
            ])
            if request:
                new_puroks = [
                    {'purok_number': p['purok'].number, **{k: v for k, v in p.items() if k != 'purok'}}
                    for p in purok_permissions_data
                ]
                log_action(
                    AuditLog.Action.PERMISSION_CHANGED,
                    actor=request.user,
                    request=request,
                    target_user=instance,
                    extra={'old_puroks': old_puroks, 'new_puroks': new_puroks},
                )

        return instance


# ---------------------------------------------------------------------------
# Resident account creation
# ---------------------------------------------------------------------------

class CreateResidentAccountSerializer(serializers.Serializer):
    """
    Links an existing Person record to a new RESIDENT user account.

    Used by ADMIN/SUPER_ADMIN from the Household detail page.
    Validates that:
      1. The person_id belongs to a real Person in the profiling DB
      2. The person does NOT already have a user account
      3. The email is not already taken
    """
    person_id = serializers.UUIDField()
    email     = serializers.EmailField()

    # Read-only response fields
    id            = serializers.IntegerField(read_only=True)
    temp_password = serializers.CharField(read_only=True)

    def validate_person_id(self, value):
        from apps.profiling.models import Person
        try:
            person = Person.objects.get(pk=value)
        except Person.DoesNotExist:
            raise serializers.ValidationError('Person not found in the profiling database.')
        # Check no existing user account
        if hasattr(person, 'user_account') and person.user_account is not None:
            raise serializers.ValidationError('This person already has a user account.')
        self._person = person
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def create(self, validated_data):
        from apps.audit.models import AuditLog
        from apps.audit.utils import log_action

        temp_password = generate_temp_password()
        request       = self.context['request']
        person        = self._person

        with transaction.atomic():
            user = User(
                email=validated_data['email'],
                first_name=person.first_name,
                last_name=person.last_name,
                role=User.Role.RESIDENT,
                is_staff=False,
                email_verified=False,
                must_change_password=True,
                person=person,
                created_by=request.user,
            )
            user.set_password(temp_password)
            user.save()

        log_action(
            AuditLog.Action.RESIDENT_ACCOUNT_LINKED,
            actor=request.user,
            request=request,
            target_user=user,
            extra={
                'person_id':   str(person.pk),
                'person_name': person.full_name,
                'email':       user.email,
            },
        )

        user.temp_password = temp_password
        return user
