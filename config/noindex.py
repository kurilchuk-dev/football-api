class NoIndexMiddleware:
    """Keeps the API and the admin out of search results: only the site should be found.

    A header rather than robots.txt, because search engines must still be able to read the API
    while they render the site.
    """

    PREFIXES = ("/api/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.PREFIXES):
            response["X-Robots-Tag"] = "noindex"
        return response
