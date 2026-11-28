import json
import re

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from ipware import get_client_ip

from .limits import allow

# The site reports itself here once per browser session; see visitors/middleware.py.
PING_PATH = "/api/visitors/ping/"

# A random id made by the browser (a UUID); anything else is refused.
VISITOR_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

MAX_BODY = 512


@csrf_exempt
@require_POST
def ping(request):
    """Remembers an anonymous id of the browser, so that people can be counted, not IP addresses.

    The id is random and stored only in the visitor's browser: it says nothing about who the
    person is. The middleware writes it to the visit log together with the other fields.
    Too many pings in an hour are answered with 429 and are not written to the log.
    """
    ip, _ = get_client_ip(request)
    if not allow("ping", ip, settings.VISIT_PING_LIMIT_PER_IP, settings.VISIT_PING_LIMIT_TOTAL):
        request.skip_visit_log = True
        return HttpResponse(status=429)
    try:
        if len(request.body) > MAX_BODY:
            return HttpResponseBadRequest("too big")
        visitor_id = str(json.loads(request.body or b"{}").get("visitor_id", "")).lower()
    except (ValueError, AttributeError):
        return HttpResponseBadRequest("bad json")
    if not VISITOR_ID.match(visitor_id):
        return HttpResponseBadRequest("bad id")
    request.visitor_id = visitor_id
    return HttpResponse(status=204)
