from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Household, FamilyMember, PersonalProfile
from .serializers import HouseholdSerializer, FamilyMemberSerializer, PersonalProfileSerializer


class HouseholdViewSet(viewsets.ModelViewSet):
    queryset = Household.objects.all()
    serializer_class = HouseholdSerializer
    permission_classes = [IsAuthenticated]


class FamilyMemberViewSet(viewsets.ModelViewSet):
    queryset = FamilyMember.objects.select_related('household', 'resident').all()
    serializer_class = FamilyMemberSerializer
    permission_classes = [IsAuthenticated]


class PersonalProfileViewSet(viewsets.ModelViewSet):
    queryset = PersonalProfile.objects.select_related('resident').all()
    serializer_class = PersonalProfileSerializer
    permission_classes = [IsAuthenticated]
