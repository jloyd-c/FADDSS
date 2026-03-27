import pyotp
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import MeSerializer
from apps.audit.models import AuditLog
from apps.audit.utils import log_action
from .serializers import (
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    TwoFASetupSerializer,
    TwoFAVerifySerializer,
    create_pre_auth_token,
)


def _jwt_pair(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

class LoginView(APIView):
    permission_classes = [AllowAny]
    allow_must_change_password = True

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})

        if not serializer.is_valid():
            log_action(
                AuditLog.Action.LOGIN_FAILED,
                request=request,
                extra={'email': request.data.get('email', ''), 'errors': serializer.errors},
            )
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data['user']

        # --- 2FA: active ---
        if user.totp_enabled:
            pre_auth_token = create_pre_auth_token(user.id)
            log_action(
                AuditLog.Action.LOGIN_SUCCESS,
                actor=user,
                request=request,
                extra={'step': '2fa_pending'},
            )
            return Response(
                {
                    'requires_2fa': True,
                    'pre_auth_token': pre_auth_token,
                    'detail': 'Enter the OTP from your authenticator app.',
                },
                status=status.HTTP_200_OK,
            )

        # --- Normal login (no 2FA) ---
        log_action(AuditLog.Action.LOGIN_SUCCESS, actor=user, request=request)

        response_data = {
            **_jwt_pair(user),
            'user': MeSerializer(user).data,
        }

        # Warn frontend if 2FA setup is still pending
        if user.require_2fa and not user.totp_enabled:
            response_data['must_setup_2fa'] = True

        # Warn frontend if email not yet verified
        if not user.email_verified:
            response_data['email_not_verified'] = True

        # Warn frontend if password change is required
        if user.must_change_password:
            response_data['must_change_password'] = True

        return Response(response_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    allow_must_change_password = True

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({'detail': 'Token is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)

        log_action(AuditLog.Action.LOGOUT, actor=request.user, request=request)
        return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

class MeView(APIView):
    permission_classes = [IsAuthenticated]
    allow_must_change_password = True

    def get(self, request):
        return Response(MeSerializer(request.user).data)


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------

class TwoFAVerifyView(APIView):
    """Step 2 of login when totp_enabled=True. Exchanges pre_auth_token + OTP for JWT."""
    permission_classes = [AllowAny]
    allow_must_change_password = True

    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        if not serializer.is_valid():
            # Log the failed attempt if we can identify the user
            attempted_user = serializer.validated_data.get('_user')
            log_action(
                AuditLog.Action.TWO_FA_FAILED,
                actor=attempted_user,
                request=request,
                extra={'errors': serializer.errors},
            )
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data['user']
        log_action(AuditLog.Action.TWO_FA_VERIFIED, actor=user, request=request)

        response_data = {
            **_jwt_pair(user),
            'user': MeSerializer(user).data,
        }
        if user.must_change_password:
            response_data['must_change_password'] = True

        return Response(response_data, status=status.HTTP_200_OK)


class TwoFASetupView(APIView):
    """
    GET  — generate (or retrieve) the TOTP secret and return the provisioning URI.
    POST — confirm with a valid OTP to activate 2FA.
    """
    permission_classes = [IsAuthenticated]
    allow_must_change_password = True

    def get(self, request):
        user = request.user
        if not user.totp_secret:
            user.totp_secret = pyotp.random_base32()
            user.save(update_fields=['totp_secret'])

        totp = pyotp.TOTP(user.totp_secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name='FADDSS Barangay')

        return Response({
            'secret': user.totp_secret,
            'otpauth_uri': uri,
            'instructions': 'Scan the QR code with Google Authenticator or Authy, then POST an OTP to confirm.',
        })

    def post(self, request):
        serializer = TwoFASetupSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.totp_enabled = True
        user.require_2fa = True
        user.save(update_fields=['totp_enabled', 'require_2fa'])

        log_action(AuditLog.Action.TWO_FA_SETUP, actor=user, request=request)
        return Response({'detail': '2FA has been successfully enabled on your account.'})


# ---------------------------------------------------------------------------
# Password management
# ---------------------------------------------------------------------------

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    allow_must_change_password = True

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(AuditLog.Action.PASSWORD_CHANGED, actor=request.user, request=request)
        return Response({'detail': 'Password changed successfully.'})


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    allow_must_change_password = True

    def get(self, request, token):
        serializer = EmailVerificationSerializer(data={'token': token})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(AuditLog.Action.EMAIL_VERIFIED, actor=user, request=request, target_user=user)
        return Response({'detail': f'Email verified successfully. Welcome, {user.full_name}!'})
