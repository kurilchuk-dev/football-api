from rest_framework import serializers

from teams.serializers import TeamSerializer

from .models import Match


class MatchSerializer(serializers.ModelSerializer):
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    # The date and the time are separate: the date may be known while the time is not.
    date = serializers.DateField(source="match_date", read_only=True, allow_null=True)
    time = serializers.TimeField(
        source="match_time", format="%H:%M", read_only=True, allow_null=True
    )
    # Full kick-off moment; null until both the date and the time are known.
    played_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "date",
            "time",
            "played_at",
            "round",
        ]
