from unittest import mock

from django.test import TestCase


class HealthTests(TestCase):
    def test_reports_ok_when_the_database_answers(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_reports_503_when_the_database_is_down(self):
        with mock.patch("config.views.connection.ensure_connection", side_effect=Exception):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 503)
