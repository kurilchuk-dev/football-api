from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from teams.models import Team

from .admin import parse_players
from .models import Player


class ParsePlayersTests(SimpleTestCase):
    def test_parses_names_and_optional_numbers(self):
        players, bad = parse_players("Іваненко Іван\nПетренко Петро 10\n\n  Сидоренко Сидір #7 ")
        self.assertEqual(
            players,
            [("Іваненко", "Іван", None), ("Петренко", "Петро", 10), ("Сидоренко", "Сидір", 7)],
        )
        self.assertEqual(bad, [])

    def test_reports_lines_it_cannot_read(self):
        players, bad = parse_players("Тільки\nДобрий Рядок")
        self.assertEqual(players, [("Добрий", "Рядок", None)])
        self.assertEqual(bad, ["Тільки"])


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class BulkAddTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("boss", "b@example.com", "pw")
        self.client.force_login(user)
        self.team = Team.objects.create(name="Черкаси ФАМ", is_our_team=True)
        self.url = reverse("admin:players_player_bulk_add")

    def test_form_opens(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Додати гравців списком")

    def test_creates_players_and_skips_duplicates(self):
        Player.objects.create(team=self.team, first_name="Іван", last_name="Іваненко", number=1)
        self.client.post(
            self.url,
            {"team": self.team.id, "lines": "Іваненко Іван\nПетренко Петро 10\nКоваль Кость 10"},
        )
        self.assertEqual(Player.objects.count(), 3)  # Іваненко was already there
        self.assertEqual(Player.objects.get(last_name="Петренко").number, 10)
        self.assertIsNone(Player.objects.get(last_name="Коваль").number)  # number 10 was taken
