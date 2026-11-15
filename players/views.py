from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets

from .models import Player, StaffMember
from .serializers import PlayerSerializer, StaffMemberSerializer

TEAM_PARAMETER = OpenApiParameter(
    name="team",
    type=int,
    description="Show only players of the team with this id",
)


@extend_schema_view(
    list=extend_schema(parameters=[TEAM_PARAMETER]),
)
class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlayerSerializer

    def get_queryset(self):
        queryset = Player.objects.filter(is_active=True)
        team = self.request.query_params.get("team")
        if team and team.isdigit():
            queryset = queryset.filter(team_id=team)
        return queryset


class StaffMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffMember.objects.all()
    serializer_class = StaffMemberSerializer
