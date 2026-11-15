from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from teams.models import Team

from .models import Match


class MatchValidationTests(TestCase):
    def setUp(self):
        self.ours = Team.objects.create(name="Черкаси ФАМ", is_our_team=True)
        self.a = Team.objects.create(name="Альфа")
        self.b = Team.objects.create(name="Браво")
        Match.objects.create(home_team=self.ours, away_team=self.a, round=1)

    def test_a_team_cannot_play_twice_in_a_round(self):
        match = Match(home_team=self.ours, away_team=self.b, round=1)
        with self.assertRaisesMessage(ValidationError, "уже грає в турі 1"):
            match.full_clean()

    def test_a_team_cannot_play_itself(self):
        with self.assertRaises(ValidationError):
            Match(home_team=self.a, away_team=self.a, round=5).full_clean()

    def test_both_scores_or_none(self):
        with self.assertRaises(ValidationError):
            Match(home_team=self.a, away_team=self.b, home_score=1, round=9).full_clean()

    def test_a_time_needs_a_date(self):
        from datetime import time

        with self.assertRaises(ValidationError):
            Match(home_team=self.a, away_team=self.b, match_time=time(10, 0)).full_clean()

    def test_only_one_team_can_be_ours(self):
        with self.assertRaises(ValidationError):
            Team(name="Ще одна", is_our_team=True).full_clean()
        with self.assertRaises(IntegrityError):
            Team.objects.create(name="І ще", is_our_team=True)
