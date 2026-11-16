from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Visit

LOCATION = {
    "country": "Україна",
    "country_code": "UA",
    "region": "Київ",
    "city": "Київ",
    "latitude": 50.45,
    "longitude": 30.52,
}


class VisitLogTests(TestCase):
    def setUp(self):
        # conftest.py switches the log off for the other tests; these ones need it
        self.enterContext(override_settings(VISIT_LOG_ENABLED=True))

    def test_api_request_is_logged_with_ip_and_location(self):
        with mock.patch("visitors.middleware.locate", return_value=LOCATION):
            self.client.get("/api/matches/", REMOTE_ADDR="8.8.8.8", HTTP_USER_AGENT="test-agent")
        visit = Visit.objects.get()
        self.assertEqual(visit.ip, "8.8.8.8")
        self.assertEqual(visit.path, "/api/matches/")
        self.assertEqual(visit.status_code, 200)
        self.assertEqual(visit.city, "Київ")
        self.assertEqual(visit.user_agent, "test-agent")

    def test_real_ip_is_taken_from_the_proxy_header(self):
        self.client.get(
            "/api/matches/", HTTP_X_FORWARDED_FOR="8.8.4.4, 10.0.0.1", REMOTE_ADDR="10.0.0.1"
        )
        self.assertEqual(Visit.objects.get().ip, "8.8.4.4")

    def test_visit_is_saved_without_a_location_database(self):
        with override_settings(GEOIP_DB_PATH="/no/such/file.mmdb"):
            from .geo import reset_reader

            reset_reader()
            self.client.get("/api/matches/", REMOTE_ADDR="8.8.8.8")
            reset_reader()
        visit = Visit.objects.get()
        self.assertEqual(visit.ip, "8.8.8.8")
        self.assertEqual(visit.city, "")

    def test_docs_admin_and_health_are_not_logged(self):
        self.client.get("/api/docs/")
        self.client.get("/api/schema/")
        self.client.get("/health/")
        self.client.get("/admin/")  # a redirect; the login page itself needs collectstatic
        self.assertEqual(Visit.objects.count(), 0)

    @override_settings(VISIT_LOG_ENABLED=False)
    def test_logging_can_be_switched_off(self):
        self.client.get("/api/matches/")
        self.assertEqual(Visit.objects.count(), 0)

    def test_a_failing_log_does_not_break_the_api(self):
        with mock.patch("visitors.middleware.Visit.objects.create", side_effect=Exception("db")):
            response = self.client.get("/api/matches/")
        self.assertEqual(response.status_code, 200)


class PurgeVisitsTests(TestCase):
    def test_removes_only_old_visits(self):
        old = Visit.objects.create(ip="1.1.1.1", path="/api/a/", method="GET", status_code=200)
        Visit.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=91))
        Visit.objects.create(ip="2.2.2.2", path="/api/b/", method="GET", status_code=200)
        call_command("purge_visits", stdout=StringIO())
        self.assertEqual(list(Visit.objects.values_list("ip", flat=True)), ["2.2.2.2"])


PLAIN_STORAGE = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)


@PLAIN_STORAGE
class StatsPageTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("boss", "b@example.com", "pw")
        self.client.force_login(self.admin)

    def visit(self, ip, path="/api/matches/", city="", country=""):
        return Visit.objects.create(
            ip=ip, path=path, method="GET", status_code=200, city=city, country=country
        )

    def test_page_counts_visits_and_unique_ips(self):
        self.visit("1.1.1.1", city="Київ", country="Україна")
        self.visit("1.1.1.1", city="Київ", country="Україна")
        self.visit("2.2.2.2", path="/api/players/")
        response = self.client.get(reverse("admin:visitors_visit_stats"))
        self.assertEqual(response.status_code, 200)
        totals = dict(response.context["totals"])
        self.assertEqual(totals["Запитів за добу"], 3)
        self.assertEqual(totals["Унікальних IP за добу"], 2)
        self.assertEqual(response.context["countries"][0]["label"], "Україна")
        self.assertEqual(response.context["countries"][0]["total"], 2)
        self.assertEqual(response.context["countries"][1]["label"], "Невідомо")
        self.assertEqual([row["label"] for row in response.context["cities"]], ["Київ"])
        self.assertEqual(response.context["paths"][0]["label"], "/api/matches/")

    def test_days_include_empty_ones_and_the_newest_is_first(self):
        old = self.visit("1.1.1.1")
        Visit.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=3))
        self.visit("2.2.2.2")
        per_day = self.client.get(reverse("admin:visitors_visit_stats")).context["per_day"]
        self.assertEqual(len(per_day), 30)
        self.assertEqual(per_day[0]["total"], 1)
        self.assertEqual([row["total"] for row in per_day[:4]], [1, 0, 0, 1])

    def test_works_without_any_visits(self):
        response = self.client.get(reverse("admin:visitors_visit_stats"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Даних ще немає.")

    def test_button_on_the_list_opens_the_page(self):
        response = self.client.get(reverse("admin:visitors_visit_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Статистика")

    def test_anonymous_user_is_sent_to_the_login(self):
        self.client.logout()
        response = self.client.get(reverse("admin:visitors_visit_stats"))
        self.assertEqual(response.status_code, 302)
