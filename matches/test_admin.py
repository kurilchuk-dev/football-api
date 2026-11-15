from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from teams.models import Team

from .models import Match

# The admin pages use static files; the test run has no collected manifest.
PLAIN_STORAGE = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)


@PLAIN_STORAGE
class AdminTestCase(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("boss", "b@example.com", "pw")
        self.client.force_login(self.admin)
        self.ours = Team.objects.create(name="Черкаси ФАМ", is_our_team=True)
        self.a = Team.objects.create(name="Альфа")
        self.b = Team.objects.create(name="Браво")
        self.c = Team.objects.create(name="Чарлі")
        self.m1 = Match.objects.create(
            home_team=self.ours,
            away_team=self.a,
            round=1,
            match_date=date(2026, 11, 15),
            match_time=time(10, 0),
        )
        self.m2 = Match.objects.create(home_team=self.b, away_team=self.c, round=1)


class MatchListTests(AdminTestCase):
    def test_list_shows_readable_titles_and_when(self):
        response = self.client.get(reverse("admin:matches_match_changelist"))
        self.assertContains(response, "Тур 1 · Черкаси ФАМ — Альфа")
        self.assertContains(response, "15.11.2026 · 10:00")
        self.assertContains(response, "дата уточнюється")

    def test_filters(self):
        url = reverse("admin:matches_match_changelist")
        ours = self.client.get(url, {"our": "1"})
        self.assertContains(ours, "Черкаси ФАМ — Альфа")
        self.assertNotContains(ours, "Браво — Чарлі")
        no_date = self.client.get(url, {"when": "no_date"})
        self.assertContains(no_date, "Браво — Чарлі")
        self.assertNotContains(no_date, "Черкаси ФАМ — Альфа")

    def test_search_by_team(self):
        response = self.client.get(reverse("admin:matches_match_changelist"), {"q": "Чарлі"})
        self.assertContains(response, "Браво — Чарлі")
        self.assertNotContains(response, "Черкаси ФАМ — Альфа")
