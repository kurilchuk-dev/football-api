from django.contrib import admin

from .models import Match


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "round",
        "match_date",
        "match_time",
    )
    list_filter = ("round", "match_date")
    fields = (
        "home_team",
        "away_team",
        "round",
        ("match_date", "match_time"),
        ("home_score", "away_score"),
    )
