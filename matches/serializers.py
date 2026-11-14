from rest_framework import serializers

from teams.serializers import TeamSerializer

from .models import Match


class MatchSerializer(serializers.ModelSerializer):
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "played_at",
            "round",
        ]
