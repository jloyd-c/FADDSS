from rest_framework import serializers
from .models import Household, FamilyMember, PersonalProfile


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        fields = '__all__'


class PersonalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalProfile
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
