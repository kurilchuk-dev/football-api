from django.contrib import admin

from .models import Player, StaffMember


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("number", "first_name", "last_name", "position", "team", "is_active")
    list_filter = ("team", "position", "is_active")
    search_fields = ("first_name", "last_name")


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "role", "team")
    list_filter = ("team", "role")
