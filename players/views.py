from rest_framework import viewsets

from .models import Player, StaffMember
from .serializers import PlayerSerializer, StaffMemberSerializer


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlayerSerializer

    def get_queryset(self):
        queryset = Player.objects.filter(is_active=True)
        position = self.request.query_params.get("position")
        if position:
            queryset = queryset.filter(position=position.upper())
        return queryset


class StaffMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffMember.objects.all()
    serializer_class = StaffMemberSerializer
