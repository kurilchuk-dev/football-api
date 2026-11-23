from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from matches.models import Match
from matches.tests import kickoff
from teams.models import Team

from .services import calculate_standings


class StandingsServiceTests(APITestCase):
    def setUp(self):
        self.a = Team.objects.create(name="Alpha")
        self.b = Team.objects.create(name="Bravo")
        self.c = Team.objects.create(name="Charlie")
        self.now = timezone.now()

    def play(self, home, away, home_score, away_score):
        return Match.objects.create(
            home_team=home,
            away_team=away,
            home_score=home_score,
            away_score=away_score,
            **kickoff(self.now - timedelta(days=1)),
        )

    def row(self, table, team):
        return next(r for r in table if r["team"]["id"] == team.id)

    def test_win_gives_three_points(self):
        self.play(self.a, self.b, 2, 0)
        table = calculate_standings()
        self.assertEqual(self.row(table, self.a)["points"], 3)
        self.assertEqual(self.row(table, self.b)["points"], 0)

    def test_draw_gives_one_point_each(self):
        self.play(self.a, self.b, 1, 1)
        table = calculate_standings()
        self.assertEqual(self.row(table, self.a)["points"], 1)
        self.assertEqual(self.row(table, self.b)["points"], 1)

    def test_goals_and_goal_difference(self):
        self.play(self.a, self.b, 3, 1)
        row = self.row(calculate_standings(), self.a)
        self.assertEqual(row["goals_for"], 3)
        self.assertEqual(row["goals_against"], 1)
        self.assertEqual(row["goal_difference"], 2)

    def test_unplayed_matches_are_ignored(self):
        Match.objects.create(
            home_team=self.a,
            away_team=self.b,
            **kickoff(self.now + timedelta(days=3)),
        )
        table = calculate_standings()
        self.assertEqual(self.row(table, self.a)["played"], 0)

    def test_team_without_matches_has_zeros(self):
        row = self.row(calculate_standings(), self.c)
        self.assertEqual(row["played"], 0)
        self.assertEqual(row["points"], 0)

    def test_sorted_by_points_then_goal_difference(self):
        self.play(self.a, self.c, 1, 0)  # Alpha 3 pts, GD +1

    def test_head_to_head_beats_goal_difference(self):
        # Alpha and Bravo both end on 3 points. Bravo has the better overall
        # goal difference (+4 vs +1), but Alpha won the mutual match.
        self.play(self.a, self.b, 1, 0)
        self.play(self.b, self.c, 5, 0)
        table = calculate_standings()
        self.assertEqual([r["team"]["name"] for r in table][:2], ["Alpha", "Bravo"])
        self.assertGreater(
            self.row(table, self.b)["goal_difference"], self.row(table, self.a)["goal_difference"]
        )

    def test_head_to_head_draw_falls_back_to_goal_difference(self):
        # Mutual match is a draw, so overall goal difference decides.
        self.play(self.a, self.b, 1, 1)
        self.play(self.b, self.c, 4, 0)
        self.play(self.a, self.c, 1, 0)
        # Alpha 4 pts (GD +1), Bravo 4 pts (GD +4)
        table = calculate_standings()
        self.assertEqual(table[0]["team"]["name"], "Bravo")

    def play_at(self, home, away, home_score, away_score, days_ago):
        return Match.objects.create(
            home_team=home,
            away_team=away,
            home_score=home_score,
            away_score=away_score,
            **kickoff(self.now - timedelta(days=days_ago)),
        )

    def test_form_is_last_five_results_oldest_first(self):
        # Alpha: oldest L, then W, D, W, W, W (6 matches) -> last five W D W W W... check order
        results = [(0, 1), (1, 0), (1, 1), (2, 0), (3, 0), (0, 2)]  # (alpha, bravo) goals
        for i, (alpha, bravo) in enumerate(results):
            self.play_at(self.a, self.b, alpha, bravo, days_ago=len(results) - i)
        form = self.row(calculate_standings(), self.a)["form"]
        self.assertEqual(form, ["W", "D", "W", "W", "L"])
        self.assertEqual(self.row(calculate_standings(), self.b)["form"], ["L", "D", "L", "L", "W"])

    def test_form_with_fewer_matches_and_none(self):
        self.play(self.a, self.b, 2, 0)
        table = calculate_standings()
        self.assertEqual(self.row(table, self.a)["form"], ["W"])
        self.assertEqual(self.row(table, self.c)["form"], [])


class StandingsApiLogoTests(APITestCase):
    def test_logo_is_null_without_upload_and_url_with_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        plain = Team.objects.create(name="Plain")
        with_logo = Team.objects.create(name="Logo")
        # Minimal valid 1x1 PNG.
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with self.settings(MEDIA_ROOT=self._tmp()):
            with_logo.logo.save("logo.png", SimpleUploadedFile("logo.png", png), save=True)
            response = self.client.get("/api/standings/")
        self.assertEqual(response.status_code, 200)
        by_name = {r["team"]["name"]: r["team"] for r in response.json()}
        self.assertIsNone(by_name[plain.name]["logo"])
        self.assertTrue(by_name["Logo"]["logo"].startswith("http://testserver/media/team_logos/"))

    def test_photo_is_null_without_upload_and_url_with_upload(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        plain = Team.objects.create(name="Plain")
        with_photo = Team.objects.create(name="Photo")
        buffer = io.BytesIO()
        Image.new("RGB", (1, 1)).save(buffer, format="PNG")
        upload = SimpleUploadedFile("team.png", buffer.getvalue())
        with self.settings(MEDIA_ROOT=self._tmp()):
            with_photo.photo.save("team.png", upload, save=True)
            response = self.client.get("/api/standings/")
        self.assertEqual(response.status_code, 200)
        by_name = {r["team"]["name"]: r["team"] for r in response.json()}
        self.assertIsNone(by_name[plain.name]["photo"])
        self.assertTrue(
            by_name["Photo"]["photo"].startswith("http://testserver/media/team_photos/")
        )

    def _tmp(self):
        import tempfile

        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return d.name
