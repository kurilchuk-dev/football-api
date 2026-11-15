import re

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import action

from teams.models import Team

from .models import Player, StaffMember


class BulkAddForm(forms.Form):
    team = forms.ModelChoiceField(Team.objects.all(), label="Команда")
    lines = forms.CharField(
        label="Гравці",
        widget=forms.Textarea(
            attrs={"rows": 14, "placeholder": "Іваненко Іван\nПетренко Петро 10"}
        ),
        help_text=(
            "Кожен гравець з нового рядка: «Прізвище Ім'я», а після імені, якщо є, номер. "
            "По батькові можна не писати, воно не зберігається."
        ),
    )


def parse_players(text):
    """Turn lines like "Іваненко Іван 10" into (last_name, first_name, number) tuples."""
    players, bad = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        number = None
        match = re.search(r"\s+#?(\d{1,3})$", line)
        if match:
            number = int(match.group(1))
            line = line[: match.start()].strip()
        words = line.split()
        if len(words) < 2:
            bad.append(raw.strip())
            continue
        players.append((words[0], words[1], number))  # a patronymic, if any, is ignored
    return players, bad


@admin.register(Player)
class PlayerAdmin(ModelAdmin):
    list_display = ("photo_preview", "last_name", "first_name", "number", "team", "is_active")
    list_display_links = ("photo_preview", "last_name")
    list_editable = ("number", "is_active")
    list_filter = ("team", "is_active")
    search_fields = ("first_name", "last_name")
    actions_list = ["bulk_add_link"]

    @admin.display(description="фото")
    def photo_preview(self, obj):
        if not obj.photo:
            return "—"
        return format_html(
            '<img src="{}" alt="" '
            'style="height:36px;width:36px;border-radius:50%;object-fit:cover">',
            obj.photo.url,
        )

    @action(description="Додати списком", icon="playlist_add", url_path="bulk-add-link")
    def bulk_add_link(self, request):
        return redirect(reverse("admin:players_player_bulk_add"))

    def get_urls(self):
        custom = [
            path(
                "bulk-add/",
                self.admin_site.admin_view(self.bulk_add_view),
                name="players_player_bulk_add",
            )
        ]
        return custom + super().get_urls()

    def bulk_add_view(self, request):
        if not self.has_add_permission(request):
            return redirect("admin:index")
        form = BulkAddForm(
            request.POST or None, initial={"team": Team.objects.filter(is_our_team=True).first()}
        )
        if request.method == "POST" and form.is_valid():
            team = form.cleaned_data["team"]
            parsed, bad = parse_players(form.cleaned_data["lines"])
            created, skipped = 0, []
            for last_name, first_name, number in parsed:
                if Player.objects.filter(
                    team=team, last_name=last_name, first_name=first_name
                ).exists():
                    skipped.append(f"{last_name} {first_name} (вже є)")
                    continue
                if number is not None and Player.objects.filter(team=team, number=number).exists():
                    number = None  # keep the player, the number can be set later
                    skipped.append(f"{last_name} {first_name} (номер зайнятий, додано без номера)")
                Player.objects.create(
                    team=team, last_name=last_name, first_name=first_name, number=number
                )
                created += 1
            messages.success(request, f"Додано гравців: {created}.")
            if skipped:
                messages.warning(request, "Пропущено або змінено: " + "; ".join(skipped))
            if bad:
                messages.error(request, "Не вдалося розібрати рядки: " + "; ".join(bad))
            return redirect("admin:players_player_changelist")
        context = {
            **self.admin_site.each_context(request),
            "title": "Додати гравців списком",
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "admin/players/bulk_add.html", context)


@admin.register(StaffMember)
class StaffMemberAdmin(ModelAdmin):
    list_display = ("first_name", "last_name", "role", "team")
    list_filter = ("team", "role")
