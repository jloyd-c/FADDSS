from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import CanManageStaff, IsSuperAdmin
from .models import User
from .serializers import (
    AdminDetailSerializer,
    CreateAdminSerializer,
    CreateStaffSerializer,
    StaffDetailSerializer,
    UpdateStaffSerializer,
    UserSerializer,
)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    CRUD for Admin accounts. Only Super Admin can access.

    POST   /api/v1/users/admins/        — create admin (returns temp_password once)
    GET    /api/v1/users/admins/        — list all admins
    GET    /api/v1/users/admins/{id}/   — retrieve admin
    PATCH  /api/v1/users/admins/{id}/   — update permissions / active status
    DELETE /api/v1/users/admins/{id}/   — delete admin
    """

    permission_classes = [IsSuperAdmin]
    search_fields = ['email', 'first_name', 'last_name', 'username']

    def get_queryset(self):
        return User.objects.filter(role=User.Role.ADMIN).select_related('created_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateAdminSerializer
        return AdminDetailSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.role == User.Role.SUPER_ADMIN:
            return Response(
                {'error': 'Super Admin accounts cannot be deleted.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffUserViewSet(viewsets.ModelViewSet):
    """
    CRUD for Staff accounts. Accessible by Super Admin and Admins with perm_manage_staff.

    POST   /api/v1/users/staff/        — create staff (returns temp_password once)
    GET    /api/v1/users/staff/        — list all staff
    GET    /api/v1/users/staff/{id}/   — retrieve staff with profile + purok permissions
    PATCH  /api/v1/users/staff/{id}/   — update basic fields
    DELETE /api/v1/users/staff/{id}/   — delete staff
    """

    permission_classes = [CanManageStaff]
    search_fields = ['email', 'first_name', 'last_name', 'username']

    def get_queryset(self):
        return (
            User.objects.filter(role=User.Role.STAFF)
            .select_related('created_by', 'staff_profile')
            .prefetch_related('purok_permissions__purok')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateStaffSerializer
        if self.action in ('update', 'partial_update'):
            return UpdateStaffSerializer
        return StaffDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'temp_password': user.temp_password,
                'message': 'Staff account created. Share the temp_password with the new staff member.',
            },
            status=status.HTTP_201_CREATED,
        )
