from django.contrib import admin

from .models import Match


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("home_team", "away_team", "home_score", "away_score", "round", "played_at")
    list_filter = ("round", "played_at")
