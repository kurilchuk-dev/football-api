from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets

from .models import Player, StaffMember
from .serializers import PlayerSerializer, StaffMemberSerializer

TEAM_PARAMETER = OpenApiParameter(
    name="team",
    type=int,
    description="Show only players of the team with this id",
)
OUR_TEAM_PARAMETER = OpenApiParameter(
    name="our_team",
    type=bool,
    description="true: show only players of our team (the one marked as ours), no id needed",
)


@extend_schema_view(
    list=extend_schema(parameters=[TEAM_PARAMETER, OUR_TEAM_PARAMETER]),
)
class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlayerSerializer

    def get_queryset(self):
        queryset = Player.objects.filter(is_active=True)
        team = self.request.query_params.get("team")
        if team and team.isdigit():
            queryset = queryset.filter(team_id=team)
        if self.request.query_params.get("our_team", "").lower() in ("1", "true"):
            queryset = queryset.filter(team__is_our_team=True)
        return queryset


class StaffMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffMember.objects.all()
    serializer_class = StaffMemberSerializer
