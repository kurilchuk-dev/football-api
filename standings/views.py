from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import StandingRowSerializer
from .services import calculate_standings


class StandingsView(APIView):
    @extend_schema(responses=StandingRowSerializer(many=True))
    def get(self, request):
        return Response(calculate_standings())
