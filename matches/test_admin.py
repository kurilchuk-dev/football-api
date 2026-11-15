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


class RoundPageTests(AdminTestCase):
    def test_lists_rounds_with_progress(self):
        response = self.client.get(reverse("admin:matches_match_rounds"))
        self.assertContains(response, "Тур 1")
        self.assertContains(response, "зіграно 0 з 2")

    def test_round_page_shows_the_matches(self):
        response = self.client.get(reverse("admin:matches_match_round", args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Черкаси ФАМ — Альфа")
        self.assertContains(response, "Браво — Чарлі")

    def _post(self, **overrides):
        data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "2",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": self.m1.id,
            "form-0-match_date": "2026-11-15",
            "form-0-match_time": "10:00",
            "form-0-home_score": "3",
            "form-0-away_score": "1",
            "form-1-id": self.m2.id,
            "form-1-match_date": "2026-11-16",
            "form-1-match_time": "",
            "form-1-home_score": "",
            "form-1-away_score": "",
        }
        data.update(overrides)
        return self.client.post(reverse("admin:matches_match_round", args=[1]), data)

    def test_saves_scores_dates_and_times_for_the_whole_round(self):
        response = self._post()
        self.assertEqual(response.status_code, 302)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.assertEqual((self.m1.home_score, self.m1.away_score), (3, 1))
        self.assertEqual(self.m2.match_date, date(2026, 11, 16))
        self.assertIsNone(self.m2.match_time)  # a date without a time is fine

    def test_a_single_score_is_rejected(self):
        response = self._post(**{"form-0-away_score": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "обох команд")
        self.m1.refresh_from_db()
        self.assertIsNone(self.m1.home_score)

    def test_a_time_without_a_date_is_rejected(self):
        response = self._post(**{"form-1-match_date": "", "form-1-match_time": "12:00"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "дату")


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


class MatchActionTests(AdminTestCase):
    def run_action(self, action, ids, **extra):
        return self.client.post(
            reverse("admin:matches_match_changelist"),
            {"action": action, "_selected_action": ids, **extra},
            follow=True,
        )

    def test_shift_forward_and_back(self):
        self.run_action("shift_forward", [self.m1.id, self.m2.id])
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.match_date, date(2026, 11, 16))
        self.run_action("shift_back", [self.m1.id])
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.match_date, date(2026, 11, 15))

    def test_clear_date_and_time(self):
        self.run_action("clear_date_time", [self.m1.id])
        self.m1.refresh_from_db()
        self.assertIsNone(self.m1.match_date)
        self.assertIsNone(self.m1.match_time)

    def test_set_date_time_asks_first_then_applies(self):
        asked = self.run_action("set_date_time", [self.m1.id, self.m2.id])
        self.assertContains(asked, "Застосувати")
        self.m2.refresh_from_db()
        self.assertIsNone(self.m2.match_date)

        self.run_action(
            "set_date_time", [self.m2.id], apply="1", match_date="2026-11-21", match_time="14:00"
        )
        self.m2.refresh_from_db()
        self.assertEqual(
            (self.m2.match_date, self.m2.match_time), (date(2026, 11, 21), time(14, 0))
        )
