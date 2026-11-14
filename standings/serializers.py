from rest_framework import serializers


class StandingTeamSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    is_our_team = serializers.BooleanField()
    logo = serializers.ImageField(allow_null=True, read_only=True)


class StandingRowSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    team = StandingTeamSerializer()
    played = serializers.IntegerField()
    won = serializers.IntegerField()
    drawn = serializers.IntegerField()
    lost = serializers.IntegerField()
    goals_for = serializers.IntegerField()
    goals_against = serializers.IntegerField()
    goal_difference = serializers.IntegerField()
    points = serializers.IntegerField()
    form = serializers.ListField(
        child=serializers.ChoiceField(choices=["W", "D", "L"]),
        help_text="Results of the last 5 matches, oldest first (W/D/L).",
    )
