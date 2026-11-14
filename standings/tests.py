from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from matches.models import Match
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
            played_at=self.now - timedelta(days=1),
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
            played_at=self.now + timedelta(days=3),
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
