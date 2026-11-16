from unittest import mock

from django.test import TestCase
from rest_framework.test import APITestCase


class HealthTests(TestCase):
    def test_liveness_answers_without_touching_the_database(self):
        with mock.patch("config.views.connection.ensure_connection") as ensure_connection:
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        ensure_connection.assert_not_called()

    def test_readiness_reports_ok_when_the_database_answers(self):
        response = self.client.get("/health/db/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_reports_503_when_the_database_is_down(self):
        with mock.patch("config.views.connection.ensure_connection", side_effect=Exception):
            response = self.client.get("/health/db/")
        self.assertEqual(response.status_code, 503)


class ApiCacheHeaderTests(APITestCase):
    def test_public_api_can_be_cached_by_a_cdn(self):
        response = self.client.get("/api/matches/")
        cache_control = response["Cache-Control"]
        self.assertIn("public", cache_control)
        self.assertIn("s-maxage=60", cache_control)
        self.assertIn("max-age=0", cache_control)

    def test_api_answers_any_origin_the_same_way(self):
        response = self.client.get("/api/matches/", HTTP_ORIGIN="https://anything.example")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Origin", response.get("Vary", ""))

    def test_health_and_admin_are_not_cached(self):
        self.assertNotIn("s-maxage", self.client.get("/health/").get("Cache-Control", ""))
        self.assertNotIn("s-maxage", self.client.get("/admin/").get("Cache-Control", ""))


class ApiCompressionTests(APITestCase):
    def test_large_api_responses_are_gzipped_when_the_client_accepts_it(self):
        response = self.client.get("/api/schema/", HTTP_ACCEPT_ENCODING="gzip")
        self.assertEqual(response["Content-Encoding"], "gzip")
        self.assertIn("Accept-Encoding", response["Vary"])

    def test_responses_stay_plain_without_accept_encoding(self):
        response = self.client.get("/api/schema/")
        self.assertNotIn("Content-Encoding", response)
