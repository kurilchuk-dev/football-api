from django.contrib import admin
from django.db.models import F, Q
from unfold.admin import ModelAdmin

from .models import Match

PLAYED = Q(home_score__isnull=False, away_score__isnull=False)


def order_by_kickoff(queryset):
    """Earliest first; matches without a date (or time) last."""
    return queryset.order_by(
        F("match_date").asc(nulls_last=True), F("match_time").asc(nulls_last=True), "id"
    )


# --- filters ---------------------------------------------------------------------------------


class OurTeamFilter(admin.SimpleListFilter):
    title = "команда"
    parameter_name = "our"

    def lookups(self, request, model_admin):
        return [("1", "Тільки наша команда")]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(Q(home_team__is_our_team=True) | Q(away_team__is_our_team=True))
        return queryset


class StatusFilter(admin.SimpleListFilter):
    title = "стан"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [("upcoming", "Ще не зіграні"), ("played", "Зіграні")]

    def queryset(self, request, queryset):
        if self.value() == "played":
            return queryset.filter(PLAYED)
        if self.value() == "upcoming":
            return queryset.exclude(PLAYED)
        return queryset


class WhenFilter(admin.SimpleListFilter):
    title = "дата і час"
    parameter_name = "when"

    def lookups(self, request, model_admin):
        return [("no_date", "Без дати"), ("no_time", "Є дата, але немає часу")]

    def queryset(self, request, queryset):
        if self.value() == "no_date":
            return queryset.filter(match_date__isnull=True)
        if self.value() == "no_time":
            return queryset.filter(match_date__isnull=False, match_time__isnull=True)
        return queryset


# --- admin -----------------------------------------------------------------------------------


@admin.register(Match)
class MatchAdmin(ModelAdmin):
    list_display = ("title", "when", "home_score", "away_score")
    list_display_links = ("title",)
    list_editable = ("home_score", "away_score")
    list_filter = (OurTeamFilter, StatusFilter, WhenFilter, "round")
    search_fields = ("home_team__name", "away_team__name")
    list_select_related = ("home_team", "away_team")
    list_per_page = 50
    ordering = ("round", "match_date", "match_time", "id")
    fields = (
        "home_team",
        "away_team",
        "round",
        ("match_date", "match_time"),
        ("home_score", "away_score"),
    )

    # list columns

    @admin.display(description="Матч", ordering="home_team__name")
    def title(self, obj):
        prefix = f"Тур {obj.round} · " if obj.round is not None else ""
        return f"{prefix}{obj.home_team} — {obj.away_team}"

    @admin.display(description="Коли", ordering="match_date")
    def when(self, obj):
        if obj.match_date is None:
            return "дата уточнюється"
        day = obj.match_date.strftime("%d.%m.%Y")
        if obj.match_time is None:
            return f"{day} · час уточнюється"
        return f"{day} · {obj.match_time:%H:%M}"
