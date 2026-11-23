from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from players.models import Player

from .models import Team


class PlayerInline(TabularInline):
    model = Player
    extra = 0
    fields = ("last_name", "first_name", "number", "photo", "is_active")
    show_change_link = True


@admin.register(Team)
class TeamAdmin(ModelAdmin):
    list_display = ("logo_preview", "name", "city", "is_our_team", "has_photo")
    list_display_links = ("logo_preview", "name")
    list_filter = ("is_our_team",)
    search_fields = ("name", "city")
    inlines = [PlayerInline]

    @admin.display(description="логотип")
    def logo_preview(self, obj):
        if not obj.logo:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:32px;width:32px;object-fit:contain">', obj.logo.url
        )

    @admin.display(description="фото команди", boolean=True)
    def has_photo(self, obj):
        return bool(obj.photo)
