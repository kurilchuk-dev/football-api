from datetime import date

from rest_framework.test import APITestCase

from matches.models import Match
from players.models import Player
from teams.models import Team


class QueryCountTests(APITestCase):
    """Every public endpoint answers with a fixed number of queries, however many rows it returns.

    A view or serializer that touches a relation per row (an N+1) would make these counts grow
    with the data and fail here.
    """

    @classmethod
    def setUpTestData(cls):
        cls.teams = [Team.objects.create(name=f"Team {i}", is_our_team=(i == 0)) for i in range(5)]
        for i in range(10):
            home, away = cls.teams[i % 5], cls.teams[(i + 1) % 5]
            played = i < 6
            Match.objects.create(
                home_team=home,
                away_team=away,
                home_score=(i % 3) if played else None,
                away_score=((i + 1) % 3) if played else None,
                match_date=date(2026, 11, 1 + i),
                round=i + 1,
            )
        for i in range(8):
            Player.objects.create(
                team=cls.teams[0], first_name=f"P{i}", last_name=f"L{i}", number=i + 1
            )

    def test_teams(self):
        with self.assertNumQueries(1):
            self.assertEqual(len(self.client.get("/api/teams/").data), 5)

    def test_players(self):
        with self.assertNumQueries(1):
            self.assertEqual(len(self.client.get("/api/players/").data), 8)

    def test_players_of_a_team(self):
        with self.assertNumQueries(1):
            response = self.client.get(f"/api/players/?team={self.teams[0].id}")
        self.assertEqual(len(response.data), 8)

    def test_matches_with_both_teams(self):
        with self.assertNumQueries(1):
            self.assertEqual(len(self.client.get("/api/matches/").data), 10)

    def test_upcoming_matches(self):
        with self.assertNumQueries(1):
            self.assertEqual(len(self.client.get("/api/matches/upcoming/").data), 4)

    def test_results(self):
        with self.assertNumQueries(1):
            self.assertEqual(len(self.client.get("/api/matches/results/").data), 6)

    def test_standings_use_one_query_for_teams_and_one_for_matches(self):
        with self.assertNumQueries(2):
            self.assertEqual(len(self.client.get("/api/standings/").data), 5)
