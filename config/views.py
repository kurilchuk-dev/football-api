from django.db import connection
from django.http import JsonResponse


def health(request):
    """Liveness probe for the platform and for uptime pings: the app process is up.

    It deliberately does not touch the database. These requests come every few minutes, and a
    connection each time would keep the serverless Postgres (Neon) awake around the clock and
    use up its free compute hours.
    """
    return JsonResponse({"status": "ok"})


def health_db(request):
    """Readiness probe: the app is up and the database answers. Use it by hand, not for pings."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
