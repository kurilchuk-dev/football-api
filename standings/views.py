from rest_framework.response import Response
from rest_framework.views import APIView

from .services import calculate_standings


class StandingsView(APIView):
    def get(self, request):
        return Response(calculate_standings())
