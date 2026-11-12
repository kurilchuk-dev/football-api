from rest_framework import status
from rest_framework.test import APITestCase

from .models import Team


class TeamApiTests(APITestCase):
    def setUp(self):
        Team.objects.create(name="Riverside", city="Kyiv")
        Team.objects.create(name="Your Team FC", is_our_team=True)

    def test_list_returns_all_teams(self):
        response = self.client.get("/api/teams/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_teams_are_sorted_by_name(self):
        response = self.client.get("/api/teams/")
        names = [team["name"] for team in response.data]
        self.assertEqual(names, ["Riverside", "Your Team FC"])

    def test_api_is_read_only(self):
        response = self.client.post("/api/teams/", {"name": "New FC"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
