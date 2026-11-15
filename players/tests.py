import shutil
import tempfile
from io import BytesIO, StringIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APITestCase

from teams.models import Team

from .models import Player, StaffMember


class PlayersApiTests(APITestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Your Team FC", is_our_team=True)
        Player.objects.create(team=self.team, first_name="A", last_name="Zed", number=1)
        Player.objects.create(team=self.team, first_name="B", last_name="Alpha", number=9)
        Player.objects.create(
            team=self.team, first_name="C", last_name="Left", number=7, is_active=False
        )

    def test_inactive_players_are_hidden(self):
        response = self.client.get("/api/players/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_players_are_sorted_by_surname(self):
        response = self.client.get("/api/players/")
        self.assertEqual([p["last_name"] for p in response.data], ["Alpha", "Zed"])

    def test_player_has_no_position_field(self):
        response = self.client.get("/api/players/")
        self.assertEqual(
            set(response.data[0]), {"id", "first_name", "last_name", "number", "photo"}
        )

    def test_filter_by_team(self):
        other = Team.objects.create(name="Other FC")
        Player.objects.create(team=other, first_name="E", last_name="Rival", number=1)
        response = self.client.get(f"/api/players/?team={self.team.id}")
        self.assertEqual(len(response.data), 2)
        response = self.client.get(f"/api/players/?team={other.id}")
        self.assertEqual(len(response.data), 1)

    def test_shirt_number_is_optional(self):
        Player.objects.create(team=self.team, first_name="N", last_name="One")
        Player.objects.create(team=self.team, first_name="N", last_name="Two")
        response = self.client.get("/api/players/")
        self.assertEqual(len(response.data), 4)
        self.assertEqual(
            [p["number"] for p in response.data if p["last_name"] in ("One", "Two")],
            [None, None],
        )

    def test_shirt_number_is_unique_per_team(self):
        with self.assertRaises(IntegrityError):
            Player.objects.create(team=self.team, first_name="D", last_name="Dup", number=1)

    def test_photo_is_empty_until_uploaded(self):
        response = self.client.get("/api/players/")
        self.assertEqual([p["photo"] for p in response.data], [None, None])

    def test_uploaded_photo_is_served_as_absolute_url(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        buffer = BytesIO()
        Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
        with override_settings(MEDIA_ROOT=media):
            player = Player.objects.get(last_name="Zed")
            player.photo = SimpleUploadedFile("face.png", buffer.getvalue(), "image/png")
            player.save()
            response = self.client.get("/api/players/")
        photos = {p["last_name"]: p["photo"] for p in response.data}
        self.assertRegex(photos["Zed"], r"^http://testserver/media/player_photos/face.*\.png$")
        self.assertIsNone(photos["Alpha"])

    def test_staff_endpoint(self):
        StaffMember.objects.create(
            team=self.team, first_name="E", last_name="Coach", role="head_coach"
        )
        response = self.client.get("/api/staff/")
        self.assertEqual(response.data[0]["role_display"], "Head coach")


class ImportRosterTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test FC", is_our_team=True)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.file = Path(directory.name) / "roster.txt"

    def run_import(self, text, *extra):
        self.file.write_text(text, encoding="utf-8")
        out = StringIO()
        call_command("import_roster", str(self.file), "--team", "Test FC", *extra, stdout=out)
        return out.getvalue()

    def test_splits_surname_from_name_and_patronymic(self):
        self.run_import("Іванов Петро Олегович\nСидоренко Свят\n")
        ivanov = Player.objects.get(last_name="Іванов")
        self.assertEqual(ivanov.first_name, "Петро Олегович")
        self.assertIsNone(ivanov.number)
        self.assertEqual(Player.objects.get(last_name="Сидоренко").first_name, "Свят")

    def test_is_idempotent_and_ignores_blank_lines_and_comments(self):
        text = "# roster\n\nІванов Петро\n"
        self.run_import(text)
        output = self.run_import(text)
        self.assertEqual(Player.objects.count(), 1)
        self.assertIn("skipped 1 existing", output)

    def test_dry_run_changes_nothing(self):
        output = self.run_import("Іванов Петро\n", "--dry-run")
        self.assertEqual(Player.objects.count(), 0)
        self.assertIn("Would add 1", output)

    def test_unknown_team_is_an_error(self):
        self.file.write_text("Іванов Петро\n", encoding="utf-8")
        with self.assertRaises(CommandError):
            call_command("import_roster", str(self.file), "--team", "Nope")
