import csv
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.db.models import Count, F, Q
from django.forms import modelformset_factory
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from unfold.admin import ModelAdmin
from unfold.decorators import action

from standings.services import calculate_standings

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


class SetDateTimeForm(forms.Form):
    match_date = forms.DateField(
        label="Дата",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text="Залиште порожнім, щоб не змінювати дату.",
    )
    match_time = forms.TimeField(
        label="Час",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        help_text="Залиште порожнім, щоб не змінювати час.",
    )


ROUND_FIELDS = ("match_date", "match_time", "home_score", "away_score")
RoundFormSet = modelformset_factory(
    Match,
    fields=ROUND_FIELDS,
    extra=0,
    widgets={
        "match_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        "match_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        "home_score": forms.NumberInput(attrs={"min": 0, "inputmode": "numeric"}),
        "away_score": forms.NumberInput(attrs={"min": 0, "inputmode": "numeric"}),
    },
)


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
    actions = ["shift_forward", "shift_back", "clear_date_time", "set_date_time", "export_csv"]
    actions_list = ["rounds_link", "export_calendar_link", "export_standings_link"]

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

    # buttons above the list

    @action(description="Внести результати по турах", icon="edit_calendar", url_path="rounds-link")
    def rounds_link(self, request):
        return redirect(reverse("admin:matches_match_rounds"))

    @action(description="Експорт календаря (CSV)", icon="download", url_path="export-calendar")
    def export_calendar_link(self, request):
        return self._calendar_csv(order_by_kickoff(self.get_queryset(request)))

    @action(description="Експорт таблиці (CSV)", icon="leaderboard", url_path="export-standings")
    def export_standings_link(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="standings.csv"'
        response.write("﻿")  # so Excel opens the Ukrainian text correctly
        writer = csv.writer(response)
        writer.writerow(
            ["Місце", "Команда", "І", "В", "Н", "П", "Забито", "Пропущено", "Різниця", "Очки"]
        )
        for row in calculate_standings():
            writer.writerow(
                [
                    row["position"],
                    row["team"]["name"],
                    row["played"],
                    row["won"],
                    row["drawn"],
                    row["lost"],
                    row["goals_for"],
                    row["goals_against"],
                    row["goal_difference"],
                    row["points"],
                ]
            )
        return response

    # actions on the selected matches

    @admin.action(description="Перенести на день вперед")
    def shift_forward(self, request, queryset):
        self._shift(request, queryset, 1)

    @admin.action(description="Перенести на день назад")
    def shift_back(self, request, queryset):
        self._shift(request, queryset, -1)

    def _shift(self, request, queryset, days):
        changed = 0
        for match in queryset.exclude(match_date__isnull=True):
            match.match_date += timedelta(days=days)
            match.save(update_fields=["match_date"])
            changed += 1
        skipped = queryset.count() - changed
        self.message_user(request, f"Перенесено матчів: {changed}.", messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Без дати, тому пропущено: {skipped}.", messages.WARNING)

    @admin.action(description="Очистити дату й час")
    def clear_date_time(self, request, queryset):
        count = queryset.update(match_date=None, match_time=None)
        self.message_user(request, f"Дату й час очищено: {count}.", messages.SUCCESS)

    @admin.action(description="Встановити дату й час…")
    def set_date_time(self, request, queryset):
        if "apply" in request.POST:
            form = SetDateTimeForm(request.POST)
            if form.is_valid():
                changes = {}
                if form.cleaned_data["match_date"]:
                    changes["match_date"] = form.cleaned_data["match_date"]
                if form.cleaned_data["match_time"]:
                    changes["match_time"] = form.cleaned_data["match_time"]
                if not changes:
                    self.message_user(
                        request, "Нічого не вказано, нічого не змінено.", messages.WARNING
                    )
                    return None
                if "match_time" in changes and "match_date" not in changes:
                    # a time needs a date: only matches that already have one can get it
                    matches = queryset.filter(match_date__isnull=False)
                    skipped = queryset.count() - matches.count()
                    if skipped:
                        self.message_user(
                            request,
                            f"Без дати, тому час не встановлено: {skipped}.",
                            messages.WARNING,
                        )
                    queryset = matches
                count = queryset.update(**changes)
                self.message_user(request, f"Оновлено матчів: {count}.", messages.SUCCESS)
                return None
        else:
            form = SetDateTimeForm()
        context = {
            **self.admin_site.each_context(request),
            "title": "Встановити дату й час",
            "form": form,
            "matches": queryset,
            "action": "set_date_time",
            "selected": request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME),
            "opts": self.model._meta,
        }
        return render(request, "admin/matches/set_date_time.html", context)

    @admin.action(description="Експорт вибраних у CSV")
    def export_csv(self, request, queryset):
        return self._calendar_csv(order_by_kickoff(queryset))

    def _calendar_csv(self, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="calendar.csv"'
        response.write("﻿")
        writer = csv.writer(response)
        writer.writerow(
            ["Тур", "Дата", "Час", "Господарі", "Гості", "Голи господарів", "Голи гостей"]
        )
        for match in queryset.select_related("home_team", "away_team"):
            writer.writerow(
                [
                    match.round if match.round is not None else "",
                    match.match_date.strftime("%d.%m.%Y") if match.match_date else "",
                    f"{match.match_time:%H:%M}" if match.match_time else "",
                    match.home_team,
                    match.away_team,
                    "" if match.home_score is None else match.home_score,
                    "" if match.away_score is None else match.away_score,
                ]
            )
        return response

    # entering results round by round

    def get_urls(self):
        wrap = self.admin_site.admin_view
        custom = [
            path("rounds/", wrap(self.rounds_view), name="matches_match_rounds"),
            path("rounds/<int:number>/", wrap(self.round_view), name="matches_match_round"),
        ]
        return custom + super().get_urls()

    def rounds_view(self, request):
        if not self.has_view_or_change_permission(request):
            return redirect("admin:index")
        rounds = (
            Match.objects.filter(round__isnull=False)
            .values("round")
            .annotate(total=Count("id"), played=Count("id", filter=PLAYED))
            .order_by("round")
        )
        rows = [
            {
                "number": item["round"],
                "total": item["total"],
                "played": item["played"],
                "url": reverse("admin:matches_match_round", args=[item["round"]]),
            }
            for item in rounds
        ]
        context = {
            **self.admin_site.each_context(request),
            "title": "Тури",
            "rows": rows,
            "opts": self.model._meta,
        }
        return render(request, "admin/matches/rounds.html", context)

    def round_view(self, request, number):
        if not self.has_change_permission(request):
            return redirect("admin:index")
        queryset = order_by_kickoff(
            Match.objects.filter(round=number).select_related("home_team", "away_team")
        )
        if request.method == "POST":
            formset = RoundFormSet(request.POST, queryset=queryset)
            if formset.is_valid():
                formset.save()
                self.message_user(request, f"Тур {number} збережено.", messages.SUCCESS)
                return redirect("admin:matches_match_round", number=number)
        else:
            formset = RoundFormSet(queryset=queryset)
        rounds = list(
            Match.objects.filter(round__isnull=False)
            .values_list("round", flat=True)
            .distinct()
            .order_by("round")
        )
        position = rounds.index(number) if number in rounds else -1
        context = {
            **self.admin_site.each_context(request),
            "title": f"Тур {number}",
            "formset": formset,
            "number": number,
            "previous": rounds[position - 1] if position > 0 else None,
            "next": rounds[position + 1] if 0 <= position < len(rounds) - 1 else None,
            "rounds_url": reverse("admin:matches_match_rounds"),
            "opts": self.model._meta,
        }
        return render(request, "admin/matches/round.html", context)
