from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ChangePasswordView,
    EmailVerificationView,
    LoginView,
    LogoutView,
    MeView,
    TwoFASetupView,
    TwoFAVerifyView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
    # Password
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    # 2FA
    path('2fa/setup/', TwoFASetupView.as_view(), name='auth-2fa-setup'),
    path('2fa/verify/', TwoFAVerifyView.as_view(), name='auth-2fa-verify'),
    # Email verification
    path('verify-email/<uuid:token>/', EmailVerificationView.as_view(), name='auth-verify-email'),
]
