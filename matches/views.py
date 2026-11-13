from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Match
from .serializers import MatchSerializer


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MatchSerializer

    def get_queryset(self):
        queryset = Match.objects.select_related("home_team", "away_team")
        team = self.request.query_params.get("team")
        if team and team.isdigit():
            queryset = queryset.filter(Q(home_team_id=team) | Q(away_team_id=team))
        return queryset

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        queryset = self.get_queryset().filter(home_score__isnull=True).order_by("played_at")
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def results(self, request):
        queryset = self.get_queryset().filter(home_score__isnull=False, away_score__isnull=False)
        return Response(self.get_serializer(queryset, many=True).data)
