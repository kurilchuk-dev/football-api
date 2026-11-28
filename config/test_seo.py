from unittest import mock

from django.test import TestCase, override_settings

from config import rebuild
from matches.models import Match
from teams.models import Team


class NoIndexTests(TestCase):
    def test_api_and_admin_ask_not_to_be_indexed(self):
        for path in ("/api/teams/", "/admin/"):
            self.assertEqual(self.client.get(path)["X-Robots-Tag"], "noindex", path)
        self.assertNotIn("X-Robots-Tag", self.client.get("/health/"))


class MatchTextTests(TestCase):
    def test_the_api_returns_the_venue_and_the_report(self):
        home, away = Team.objects.create(name="A"), Team.objects.create(name="B")
        Match.objects.create(home_team=home, away_team=away, venue="Зала", report="Звіт")
        match = self.client.get("/api/matches/").data[0]
        self.assertEqual((match["venue"], match["report"]), ("Зала", "Звіт"))


class RebuildTests(TestCase):
    def test_without_a_hook_nothing_is_scheduled(self):
        with mock.patch.object(rebuild, "_start_timer") as start:
            with self.captureOnCommitCallbacks(execute=True):
                Team.objects.create(name="A")
        start.assert_not_called()

    @override_settings(SITE_DEPLOY_HOOK_URL="https://example.com/hook")
    def test_saving_and_deleting_schedule_a_build(self):
        with mock.patch.object(rebuild, "_start_timer") as start:
            with self.captureOnCommitCallbacks(execute=True):
                team = Team.objects.create(name="A")
            with self.captureOnCommitCallbacks(execute=True):
                team.delete()
        self.assertEqual(start.call_count, 2)

    @override_settings(SITE_DEPLOY_HOOK_URL="https://example.com/hook")
    def test_a_new_edit_postpones_the_build(self):
        with mock.patch.object(rebuild.threading, "Timer") as timer:
            rebuild._timer = None
            rebuild._start_timer()
            rebuild._start_timer()
        self.assertEqual(timer.return_value.cancel.call_count, 1)
        rebuild._timer = None

    @override_settings(SITE_DEPLOY_HOOK_URL="https://example.com/secret-hook")
    def test_a_failed_call_is_logged_without_the_secret_address(self):
        error = rebuild.requests.ConnectionError("https://example.com/secret-hook")
        with mock.patch.object(rebuild.requests, "post", side_effect=error):
            with self.assertLogs("config.rebuild", "WARNING") as logs:
                rebuild._call_hook()
        self.assertNotIn("secret-hook", "".join(logs.output))
