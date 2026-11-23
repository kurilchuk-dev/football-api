from datetime import timedelta

from django.contrib import admin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.decorators import action

from .models import Visit

DAYS = 30
TOP = 10


def with_share(rows, label):
    """Turn `values()` rows into {label, total, percent}; the widest bar is 100%."""
    biggest = max((row["total"] for row in rows), default=0)
    return [
        {
            "label": row[label] or "Невідомо",
            "total": row["total"],
            "percent": round(row["total"] * 100 / biggest) if biggest else 0,
        }
        for row in rows
    ]


def top(queryset, field):
    rows = queryset.values(field).annotate(total=Count("id")).order_by("-total", field)[:TOP]
    return with_share(list(rows), field)


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
    actions_list = ["stats_link"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # button above the list

    @action(description="Статистика", icon="bar_chart", url_path="stats-link")
    def stats_link(self, request):
        return redirect(reverse("admin:visitors_visit_stats"))

    def get_urls(self):
        custom = [
            path(
                "stats/", self.admin_site.admin_view(self.stats_view), name="visitors_visit_stats"
            ),
        ]
        return custom + super().get_urls()

    def stats_view(self, request):
        if not self.has_view_permission(request):
            return redirect("admin:index")

        now = timezone.now()
        visits = Visit.objects.all()
        day_ago = visits.filter(created_at__gte=now - timedelta(days=1))
        week_ago = visits.filter(created_at__gte=now - timedelta(days=7))
        totals = [
            ("Запитів за добу", day_ago.count()),
            ("Унікальних IP за добу", day_ago.values("ip").distinct().count()),
            ("Запитів за 7 днів", week_ago.count()),
            ("Унікальних IP за 7 днів", week_ago.values("ip").distinct().count()),
            ("Запитів усього", visits.count()),
            ("Унікальних IP усього", visits.values("ip").distinct().count()),
        ]

        # one row for every one of the last DAYS days, also the empty ones
        # The visits are grouped by the local (Kyiv) day, so the days are counted in local time too:
        # in UTC, between 00:00 and 03:00 in Kyiv "today" would be the previous day and be lost.
        since = timezone.localtime(now).date() - timedelta(days=DAYS - 1)
        counted = {
            row["day"]: row
            for row in visits.filter(created_at__date__gte=since)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"), unique=Count("ip", distinct=True))
        }
        per_day = []
        for offset in range(DAYS):
            day = since + timedelta(days=offset)
            row = counted.get(day, {})
            per_day.append(
                {"label": day, "total": row.get("total", 0), "unique": row.get("unique", 0)}
            )
        biggest = max((row["total"] for row in per_day), default=0)
        for row in per_day:
            row["percent"] = round(row["total"] * 100 / biggest) if biggest else 0
        per_day.reverse()  # the newest day first

        context = {
            **self.admin_site.each_context(request),
            "title": "Статистика відвідувачів",
            "opts": self.model._meta,
            "list_url": reverse("admin:visitors_visit_changelist"),
            "totals": totals,
            "days": DAYS,
            "per_day": per_day,
            "countries": top(visits, "country"),
            "cities": top(visits.exclude(city=""), "city"),
            "paths": top(visits, "path"),
            "ips": top(visits, "ip"),
        }
        return render(request, "admin/visitors/stats.html", context)
