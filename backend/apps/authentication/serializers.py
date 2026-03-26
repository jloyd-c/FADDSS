import pyotp
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from rest_framework import serializers

from apps.accounts.models import User

# Salt used for signing pre-auth tokens during 2FA login flow.
_PRE_AUTH_SALT = 'faddss-pre-auth-2fa'
_PRE_AUTH_TTL = 300  # 5 minutes


def create_pre_auth_token(user_id: int) -> str:
    return signing.dumps({'user_id': user_id}, salt=_PRE_AUTH_SALT)


def verify_pre_auth_token(token: str):
    """Returns user_id on success, None on failure/expiry."""
    try:
        data = signing.loads(token, salt=_PRE_AUTH_SALT, max_age=_PRE_AUTH_TTL)
        return data['user_id']
    except (signing.BadSignature, signing.SignatureExpired, KeyError):
        return None


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        request = self.context.get('request')
        email = attrs['email']
        password = attrs['password']

        user = authenticate(request=request, username=email, password=password)

        if not user:
            raise serializers.ValidationError(
                {'non_field_errors': 'Invalid email or password.'},
                code='authorization',
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {'non_field_errors': 'This account has been deactivated.'},
                code='authorization',
            )

        # IP whitelist check for ADMIN / SUPER_ADMIN
        if user.role in ('ADMIN', 'SUPER_ADMIN') and user.ip_whitelist.exists():
            from apps.audit.utils import get_client_ip
            client_ip = get_client_ip(request) if request else None
            allowed_ips = list(user.ip_whitelist.values_list('ip_address', flat=True))
            if client_ip not in allowed_ips:
                raise serializers.ValidationError(
                    {'non_field_errors': 'Login denied: your IP address is not whitelisted.'},
                    code='ip_not_whitelisted',
                )

        attrs['user'] = user
        return attrs


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------

class TwoFAVerifySerializer(serializers.Serializer):
    """Step 2 of login when 2FA is active — trades pre_auth_token + OTP for JWT."""

    pre_auth_token = serializers.CharField()
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        user_id = verify_pre_auth_token(attrs['pre_auth_token'])
        if user_id is None:
            raise serializers.ValidationError(
                {'pre_auth_token': 'Token is invalid or has expired. Please log in again.'}
            )
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'pre_auth_token': 'User not found.'})

        if not user.totp_enabled or not user.totp_secret:
            raise serializers.ValidationError({'otp': '2FA is not set up for this account.'})

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(attrs['otp'], valid_window=1):
            attrs['_user'] = user
            raise serializers.ValidationError({'otp': 'Invalid or expired OTP code.'})

        attrs['user'] = user
        return attrs


class TwoFASetupSerializer(serializers.Serializer):
    """Confirm 2FA setup — user submits OTP generated from the just-issued secret."""

    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_otp(self, value):
        user = self.context['request'].user
        if not user.totp_secret:
            raise serializers.ValidationError('No TOTP secret found. Call GET first to generate one.')
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(value, valid_window=1):
            raise serializers.ValidationError('Invalid OTP. Scan the QR code again and retry.')
        return value


# ---------------------------------------------------------------------------
# Password management
# ---------------------------------------------------------------------------

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        validate_password(attrs['new_password'], user=self.context['request'].user)
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        return user


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.UUIDField()

    def validate_token(self, value):
        from apps.accounts.models import EmailVerification
        try:
            verification = EmailVerification.objects.select_related('user').get(token=value)
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError('Verification link is invalid.')
        if verification.is_used:
            raise serializers.ValidationError('This link has already been used.')
        if verification.is_expired:
            raise serializers.ValidationError('This verification link has expired.')
        return verification

    def save(self):
        verification = self.validated_data['token']
        verification.mark_verified()
        return verification.user
