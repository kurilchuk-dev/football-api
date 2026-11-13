from django.urls import path

from .views import StandingsView

urlpatterns = [
    path("standings/", StandingsView.as_view(), name="standings"),
]
