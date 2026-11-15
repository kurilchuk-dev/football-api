from datetime import UTC
from io import StringIO
from itertools import combinations

from django.core.management import call_command
from django.test import TestCase

from teams.models import Team

from .management.commands.seed_calendar import CALENDAR, OUR_TEAM, iter_matches
from .models import Match


class CalendarDataTests(TestCase):
    """The calendar was typed from a photo, so check that it is a valid round robin."""

    def test_has_13_teams_13_rounds_and_78_matches(self):
        matches = list(iter_matches())
        teams = {team for _, _, home, away in matches for team in (home, away)}
        self.assertEqual(len(teams), 13)
        self.assertEqual(len(CALENDAR), 13)
        self.assertEqual(len(matches), 78)

    def test_every_pair_of_teams_meets_exactly_once(self):
        matches = list(iter_matches())
        pairs = [frozenset((home, away)) for _, _, home, away in matches]
        teams = {team for _, _, home, away in matches for team in (home, away)}
        self.assertEqual(len(set(pairs)), 78)
        self.assertEqual(set(pairs), {frozenset(pair) for pair in combinations(teams, 2)})

    def test_each_round_has_12_different_teams(self):
        by_round = {}
        for round_number, _, home, away in iter_matches():
            by_round.setdefault(round_number, []).extend([home, away])
        for round_number, teams in by_round.items():
            self.assertEqual(len(teams), len(set(teams)), f"round {round_number}")
            self.assertEqual(len(teams), 12)

    def test_round_1_has_the_times_from_the_calendar(self):
        first = [m for m in iter_matches() if m[0] == 1]
        self.assertEqual(
            [m[1].strftime("%H:%M") for m in first],
            ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
        )
        # Kyiv winter time is UTC+2.
        self.assertEqual(first[0][1].astimezone(UTC).hour, 8)


class SeedCalendarCommandTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("seed_calendar", *args, stdout=out)
        return out.getvalue()

    def test_seeds_an_empty_database(self):
        output = self.run_command()
        self.assertEqual(Team.objects.count(), 13)
        self.assertEqual(Match.objects.count(), 78)
        self.assertIn("Added 13 team(s) and 78 match(es)", output)
        self.assertEqual(Team.objects.filter(is_our_team=True).get().name, OUR_TEAM)
        self.assertFalse(Match.objects.filter(home_score__isnull=False).exists())

    def test_does_nothing_when_matches_exist(self):
        self.run_command()
        Match.objects.filter(round=13).delete()  # an admin deleted something on purpose
        output = self.run_command()
        self.assertIn("nothing to seed", output)
        self.assertEqual(Match.objects.count(), 72)

    def test_force_adds_only_what_is_missing(self):
        self.run_command()
        Match.objects.filter(round=13).delete()
        self.run_command("--force")
        self.assertEqual(Team.objects.count(), 13)
        self.assertEqual(Match.objects.count(), 78)

    def test_reuses_an_existing_team_with_the_same_name(self):
        Team.objects.create(name=OUR_TEAM, is_our_team=True)
        self.run_command()
        self.assertEqual(Team.objects.filter(name=OUR_TEAM).count(), 1)
        self.assertEqual(Team.objects.count(), 13)
