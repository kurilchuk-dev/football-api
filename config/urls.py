from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("teams.urls")),
    path("api/", include("matches.urls")),
    path("api/", include("standings.urls")),
    path("api/", include("players.urls")),
]
