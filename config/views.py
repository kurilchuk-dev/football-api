from django.db import connection
from django.http import JsonResponse


def health(request):
    """Liveness/readiness probe for the hosting platform: the app is up and the DB answers."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
