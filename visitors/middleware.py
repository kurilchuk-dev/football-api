import logging

from django.conf import settings
from ipware import get_client_ip

from .geo import locate
from .limits import allow
from .models import Visit

logger = logging.getLogger(__name__)

# Documentation pages are not visits to the data.
SKIPPED_PREFIXES = ("/api/docs/", "/api/schema/")


class VisitLogMiddleware:
    """Stores the IP, the approximate location and the requested path of every /api/ request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            settings.VISIT_LOG_ENABLED
            and request.path.startswith("/api/")
            and not request.path.startswith(SKIPPED_PREFIXES)
            and not getattr(request, "skip_visit_log", False)
        ):
            self._log(request, response)
        return response

    def _log(self, request, response):
        try:
            ip, _ = get_client_ip(request)
            visitor_id = getattr(request, "visitor_id", "")
            # An accepted ping has its own limit (see views.ping) and is always written.
            if not visitor_id and not allow(
                "log", ip, settings.VISIT_LOG_LIMIT_PER_IP, settings.VISIT_LOG_LIMIT_TOTAL
            ):
                return
            Visit.objects.create(
                ip=ip,
                visitor_id=visitor_id,
                path=request.path[:255],
                method=request.method,
                status_code=response.status_code,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
                **locate(ip),
            )
        except Exception:  # a broken log must never break the API
            logger.exception("Could not log a visit")
