from rest_framework import serializers

from .models import Player, StaffMember


class PlayerSerializer(serializers.ModelSerializer):
    position_display = serializers.CharField(source="get_position_display", read_only=True)

    class Meta:
        model = Player
        fields = ["id", "first_name", "last_name", "number", "position", "position_display"]


class StaffMemberSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = StaffMember
        fields = ["id", "first_name", "last_name", "role", "role_display"]
