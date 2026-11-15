from datetime import date, timedelta
from datetime import time as datetime_time

from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from teams.models import Team

from .models import Match


def kickoff(moment):
    """The match_date/match_time (Kyiv time) of a datetime, for Match.objects.create(**...)."""
    local = timezone.localtime(moment)
    return {"match_date": local.date(), "match_time": local.time().replace(microsecond=0)}


class MatchApiTests(APITestCase):
    def setUp(self):
        self.home = Team.objects.create(name="Your Team FC", is_our_team=True)
        self.away = Team.objects.create(name="Riverside")
        now = timezone.now()
        self.old = Match.objects.create(
            home_team=self.home,
            away_team=self.away,
            home_score=2,
            away_score=1,
            **kickoff(now - timedelta(days=7)),
        )
        self.new = Match.objects.create(
            home_team=self.away,
            away_team=self.home,
            **kickoff(now + timedelta(days=7)),
        )

    def test_list_returns_matches(self):
        response = self.client.get("/api/matches/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_matches_are_newest_first(self):
        response = self.client.get("/api/matches/")
        self.assertEqual(response.data[0]["id"], self.new.id)

    def test_match_contains_team_names_and_score(self):
        response = self.client.get(f"/api/matches/{self.old.id}/")
        self.assertEqual(response.data["home_team"]["name"], "Your Team FC")
        self.assertEqual(response.data["home_score"], 2)

    def test_upcoming_match_has_no_score(self):
        response = self.client.get(f"/api/matches/{self.new.id}/")
        self.assertIsNone(response.data["home_score"])

    def test_team_cannot_play_itself(self):
        with self.assertRaises(IntegrityError):
            Match.objects.create(
                home_team=self.home, away_team=self.home, **kickoff(timezone.now())
            )

    def test_api_is_read_only(self):
        response = self.client.post("/api/matches/", {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_upcoming_returns_only_matches_without_score(self):
        response = self.client.get("/api/matches/upcoming/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.new.id)

    def test_results_returns_only_finished_matches(self):
        response = self.client.get("/api/matches/results/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.old.id)

    def test_filter_by_team(self):
        other = Team.objects.create(name="Northgate")
        Match.objects.create(home_team=other, away_team=self.away, **kickoff(timezone.now()))
        response = self.client.get(f"/api/matches/?team={self.home.id}")
        self.assertEqual(len(response.data), 2)

    def test_date_is_optional_and_undated_matches_go_last(self):
        undated = Match.objects.create(home_team=self.home, away_team=self.away, match_date=None)
        response = self.client.get(f"/api/matches/{undated.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["played_at"])

        # The list and the upcoming list put the match without a date after dated ones.
        self.assertEqual(self.client.get("/api/matches/").data[-1]["id"], undated.id)
        upcoming = self.client.get("/api/matches/upcoming/").data
        self.assertEqual([m["id"] for m in upcoming], [self.new.id, undated.id])

    def test_date_without_time_is_allowed(self):
        today = timezone.localdate()
        only_date = Match.objects.create(
            home_team=self.home, away_team=self.away, match_date=today + timedelta(days=30)
        )
        data = self.client.get(f"/api/matches/{only_date.id}/").data
        self.assertEqual(data["date"], str(today + timedelta(days=30)))
        self.assertIsNone(data["time"])
        self.assertIsNone(data["played_at"])  # no countdown without a time

        # Matches with a date and time come before the one without a time on the same day.
        later_same_day = Match.objects.create(
            home_team=self.away,
            away_team=self.home,
            match_date=only_date.match_date,
            match_time=datetime_time(18, 30),
        )
        ids = [m["id"] for m in self.client.get("/api/matches/upcoming/").data]
        self.assertEqual(ids, [self.new.id, later_same_day.id, only_date.id])

    def test_time_is_exposed_as_hh_mm_and_played_at_combines_both(self):
        match = Match.objects.create(
            home_team=self.home,
            away_team=self.away,
            match_date=date(2026, 11, 21),
            match_time=datetime_time(14, 0),
        )
        data = self.client.get(f"/api/matches/{match.id}/").data
        self.assertEqual(data["date"], "2026-11-21")
        self.assertEqual(data["time"], "14:00")
        self.assertTrue(data["played_at"].startswith("2026-11-21T14:00:00"))

    def test_time_without_a_date_is_rejected(self):
        with self.assertRaises(IntegrityError):
            Match.objects.create(
                home_team=self.home, away_team=self.away, match_time=datetime_time(10, 0)
            )

    def test_round_is_exposed_and_optional(self):
        self.old.round = 5
        self.old.save()
        response = self.client.get(f"/api/matches/{self.old.id}/")
        self.assertEqual(response.data["round"], 5)
        response = self.client.get(f"/api/matches/{self.new.id}/")
        self.assertIsNone(response.data["round"])
