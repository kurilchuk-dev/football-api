from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Visit


@admin.register(Visit)
class VisitAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "ip",
        "country",
        "region",
        "city",
        "method",
        "path",
        "status_code",
    )
    list_filter = ("country", "status_code", "method")
    search_fields = ("ip", "city", "path")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
