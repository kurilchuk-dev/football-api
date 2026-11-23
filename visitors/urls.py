from django.urls import path

from .views import ping

urlpatterns = [
    path("visitors/ping/", ping, name="visitors-ping"),
]
