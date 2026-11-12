from rest_framework import viewsets

from .models import Match
from .serializers import MatchSerializer


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Match.objects.select_related("home_team", "away_team")
    serializer_class = MatchSerializer
