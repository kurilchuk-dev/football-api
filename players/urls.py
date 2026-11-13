from rest_framework.routers import DefaultRouter

from .views import PlayerViewSet, StaffMemberViewSet

router = DefaultRouter()
router.register("players", PlayerViewSet, basename="player")
router.register("staff", StaffMemberViewSet, basename="staff")

urlpatterns = router.urls
