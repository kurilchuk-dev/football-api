from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import health, health_db

urlpatterns = [
    path("health/", health, name="health"),
    path("health/db/", health_db, name="health-db"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("admin/", admin.site.urls),
    path("api/", include("teams.urls")),
    path("api/", include("matches.urls")),
    path("api/", include("standings.urls")),
    path("api/", include("players.urls")),
    path("api/", include("visitors.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
