from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from teams.models import Team

from .models import Match


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
            played_at=now - timedelta(days=7),
        )
        self.new = Match.objects.create(
            home_team=self.away,
            away_team=self.home,
            played_at=now + timedelta(days=7),
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
            Match.objects.create(home_team=self.home, away_team=self.home, played_at=timezone.now())

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
        Match.objects.create(home_team=other, away_team=self.away, played_at=timezone.now())
        response = self.client.get(f"/api/matches/?team={self.home.id}")
        self.assertEqual(len(response.data), 2)

    def test_date_is_optional_and_undated_matches_go_last(self):
        undated = Match.objects.create(home_team=self.home, away_team=self.away, played_at=None)
        response = self.client.get(f"/api/matches/{undated.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["played_at"])

        # The list and the upcoming list put the match without a date after dated ones.
        self.assertEqual(self.client.get("/api/matches/").data[-1]["id"], undated.id)
        upcoming = self.client.get("/api/matches/upcoming/").data
        self.assertEqual([m["id"] for m in upcoming], [self.new.id, undated.id])

    def test_round_is_exposed_and_optional(self):
        self.old.round = 5
        self.old.save()
        response = self.client.get(f"/api/matches/{self.old.id}/")
        self.assertEqual(response.data["round"], 5)
        response = self.client.get(f"/api/matches/{self.new.id}/")
        self.assertIsNone(response.data["round"])
