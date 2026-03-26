from rest_framework import serializers

from apps.common.utils import generate_resident_id, get_unique_username
from .models import Purok, Resident


class PurokSerializer(serializers.ModelSerializer):
    resident_count = serializers.SerializerMethodField()

    class Meta:
        model = Purok
        fields = ('id', 'number', 'name', 'description', 'is_active', 'resident_count', 'created_at')
        read_only_fields = ('id', 'created_at', 'resident_count')

    def get_resident_count(self, obj):
        return obj.residents.count()


class ResidentSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    has_account = serializers.ReadOnlyField()
    purok_number = serializers.IntegerField(source='purok.number', read_only=True)

    class Meta:
        model = Resident
        fields = '__all__'
        read_only_fields = ('id', 'resident_id', 'has_account', 'created_at', 'updated_at')


class CreateResidentSerializer(serializers.ModelSerializer):
    """
    Step 1: Create a resident record with no user account.
    The `user` field is intentionally excluded — accounts are created separately.
    """

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    class Meta:
        model = Resident
        exclude = ('user',)
        read_only_fields = ('id', 'resident_id', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['resident_id'] = generate_resident_id()
        return super().create(validated_data)


class CreateResidentAccountSerializer(serializers.Serializer):
    """
    Step 2: Create a portal user account for an existing resident record.
    Linked via resident.user OneToOneField.
    """

    username = serializers.CharField(max_length=150, required=False, allow_blank=True)

    # Read-only response fields
    temp_password = serializers.CharField(read_only=True)

    def validate_username(self, value):
        if not value:
            return value
        from apps.accounts.models import User
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate(self, data):
        resident = self.context['resident']
        if resident.has_account:
            raise serializers.ValidationError('This resident already has a portal account.')
        if not resident.email:
            raise serializers.ValidationError(
                'Resident must have an email address before creating an account.'
            )
        return data

    def create(self, validated_data):
        from apps.accounts.models import User
        from apps.common.utils import generate_temp_password

        resident = self.context['resident']
        username = (
            validated_data.get('username')
            or get_unique_username(resident.first_name, resident.last_name)
        )

        temp_password = generate_temp_password()
        user = User(
            email=resident.email,
            username=username,
            first_name=resident.first_name,
            last_name=resident.last_name,
            role=User.Role.RESIDENT,
            is_staff=False,
            must_change_password=True,
            created_by=self.context['request'].user,
        )
        user.set_password(temp_password)
        user.save()

        resident.user = user
        resident.save(update_fields=['user'])

        from apps.audit.models import AuditLog
        from apps.audit.utils import log_action
        log_action(
            AuditLog.Action.RESIDENT_ACCOUNT_CREATED,
            actor=self.context['request'].user,
            request=self.context['request'],
            target_user=user,
            extra={'resident_id': resident.resident_id, 'resident_name': resident.full_name},
        )

        user.temp_password = temp_password
        return user
