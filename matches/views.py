from django.db.models import F, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Match
from .serializers import MatchSerializer

TEAM_PARAMETER = OpenApiParameter(
    name="team",
    type=int,
    description="Show only matches of the team with this id",
)


@extend_schema_view(
    list=extend_schema(parameters=[TEAM_PARAMETER]),
)
class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MatchSerializer

    def get_queryset(self):
        queryset = Match.objects.select_related("home_team", "away_team")
        team = self.request.query_params.get("team")
        if team and team.isdigit():
            queryset = queryset.filter(Q(home_team_id=team) | Q(away_team_id=team))
        return queryset

    @extend_schema(parameters=[TEAM_PARAMETER], responses=MatchSerializer(many=True))
    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        queryset = (
            self.get_queryset()
            .filter(home_score__isnull=True)
            .order_by(
                F("match_date").asc(nulls_last=True),
                F("match_time").asc(nulls_last=True),
                "id",
            )
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @extend_schema(parameters=[TEAM_PARAMETER], responses=MatchSerializer(many=True))
    @action(detail=False, methods=["get"])
    def results(self, request):
        queryset = self.get_queryset().filter(home_score__isnull=False, away_score__isnull=False)
        return Response(self.get_serializer(queryset, many=True).data)
