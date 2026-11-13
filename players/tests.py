from django.db import IntegrityError
from rest_framework.test import APITestCase

from teams.models import Team

from .models import Player, StaffMember


class PlayersApiTests(APITestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Your Team FC", is_our_team=True)
        Player.objects.create(
            team=self.team, first_name="A", last_name="One", number=1, position="GK"
        )
        Player.objects.create(
            team=self.team, first_name="B", last_name="Two", number=9, position="FW"
        )
        Player.objects.create(
            team=self.team,
            first_name="C",
            last_name="Left",
            number=7,
            position="MF",
            is_active=False,
        )

    def test_inactive_players_are_hidden(self):
        response = self.client.get("/api/players/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_filter_by_position(self):
        response = self.client.get("/api/players/?position=gk")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["position_display"], "Goalkeeper")

    def test_shirt_number_is_unique_per_team(self):
        with self.assertRaises(IntegrityError):
            Player.objects.create(
                team=self.team, first_name="D", last_name="Dup", number=1, position="DF"
            )

    def test_staff_endpoint(self):
        StaffMember.objects.create(
            team=self.team, first_name="E", last_name="Coach", role="head_coach"
        )
        response = self.client.get("/api/staff/")
        self.assertEqual(response.data[0]["role_display"], "Head coach")
