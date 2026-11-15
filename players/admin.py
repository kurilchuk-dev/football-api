from django.contrib import admin

from .models import Player, StaffMember


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "number", "has_photo", "team", "is_active")
    list_filter = ("team", "is_active")
    search_fields = ("first_name", "last_name")

    @admin.display(boolean=True, description="Photo")
    def has_photo(self, obj):
        return bool(obj.photo)


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "role", "team")
    list_filter = ("team", "role")
