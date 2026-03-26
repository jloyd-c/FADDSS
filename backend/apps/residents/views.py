from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import CanManageResidents, IsAdmin
from .models import Purok, Resident
from .serializers import (
    CreateResidentAccountSerializer,
    CreateResidentSerializer,
    PurokSerializer,
    ResidentSerializer,
)


class PurokViewSet(viewsets.ModelViewSet):
    """
    GET    /api/v1/residents/puroks/       — list (all authenticated)
    POST   /api/v1/residents/puroks/       — create (admin+)
    PATCH  /api/v1/residents/puroks/{id}/  — update (admin+)
    DELETE /api/v1/residents/puroks/{id}/  — delete (admin+)
    """

    queryset = Purok.objects.all()
    serializer_class = PurokSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAdmin()]


class ResidentViewSet(viewsets.ModelViewSet):
    """
    CRUD for resident records + account creation action.

    POST   /api/v1/residents/residents/               — create resident record (no account)
    GET    /api/v1/residents/residents/               — list residents
    GET    /api/v1/residents/residents/{id}/          — retrieve resident
    PATCH  /api/v1/residents/residents/{id}/          — update resident
    DELETE /api/v1/residents/residents/{id}/          — delete resident
    POST   /api/v1/residents/residents/{id}/create-account/ — create portal account
    """

    permission_classes = [CanManageResidents]
    search_fields = ['first_name', 'last_name', 'middle_name', 'resident_id', 'contact_number', 'email']

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateResidentSerializer
        return ResidentSerializer

    def get_queryset(self):
        user = self.request.user

        base_qs = Resident.objects.select_related('user', 'purok')

        # Staff can only see residents in their assigned puroks.
        if user.role == 'STAFF':
            assigned_purok_ids = user.purok_permissions.filter(
                can_view=True
            ).values_list('purok_id', flat=True)
            return base_qs.filter(purok_id__in=assigned_purok_ids)

        return base_qs.all()

    @action(detail=True, methods=['post'], url_path='create-account')
    def create_account(self, request, pk=None):
        """
        Step 2 of resident onboarding: create a portal user account
        and link it to an existing resident record.
        """
        resident = self.get_object()

        serializer = CreateResidentAccountSerializer(
            data=request.data,
            context={'request': request, 'resident': resident},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                'message': 'Portal account created. Share the credentials with the resident.',
                'resident_id': resident.resident_id,
                'resident_name': resident.full_name,
                'username': user.username,
                'email': user.email,
                'temp_password': user.temp_password,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='suggested-username')
    def suggested_username(self, request, pk=None):
        """Return the auto-generated username for the resident before account creation."""
        from apps.common.utils import get_unique_username

        resident = self.get_object()
        if resident.has_account:
            return Response({'username': resident.user.username, 'already_exists': True})
        username = get_unique_username(resident.first_name, resident.last_name)
        return Response({'username': username, 'already_exists': False})
