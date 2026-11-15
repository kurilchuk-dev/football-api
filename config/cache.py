from django.conf import settings
from django.utils.cache import patch_cache_control


class PublicApiCacheMiddleware:
    """Lets a CDN (Cloudflare) cache the public, read-only API for a short time.

    Browsers always revalidate (max-age=0), the CDN may serve a copy for
    API_CACHE_SECONDS, so an edit in the admin shows up within that time.
    Only successful GET/HEAD responses under /api/ are touched.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        seconds = settings.API_CACHE_SECONDS
        if (
            seconds > 0
            and request.method in ("GET", "HEAD")
            and request.path.startswith("/api/")
            and response.status_code == 200
        ):
            patch_cache_control(
                response,
                public=True,
                max_age=0,
                s_maxage=seconds,
                stale_while_revalidate=seconds * 5,
            )
        return response
