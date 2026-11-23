from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .bots import bot_visits, human_visits
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


GOOD_ID = "3f2b8c1e-5a4d-4e6f-9b7a-1c2d3e4f5a6b"


class PingTests(TestCase):
    def setUp(self):
        self.enterContext(override_settings(VISIT_LOG_ENABLED=True))

    def post(self, body, content_type="application/json", **extra):
        return self.client.post("/api/visitors/ping/", body, content_type=content_type, **extra)

    def test_the_id_of_the_browser_is_saved_in_the_log(self):
        response = self.post({"visitor_id": GOOD_ID}, REMOTE_ADDR="8.8.8.8")
        self.assertEqual(response.status_code, 204)
        visit = Visit.objects.get()
        self.assertEqual(visit.visitor_id, GOOD_ID)
        self.assertEqual(visit.path, "/api/visitors/ping/")
        self.assertEqual(visit.method, "POST")

    def test_an_id_that_is_not_a_uuid_is_refused_and_not_saved(self):
        for body in ({"visitor_id": "hello"}, {"visitor_id": ""}, {}, {"visitor_id": 5}):
            self.assertEqual(self.post(body).status_code, 400)
        self.assertEqual(self.post("not json", content_type="text/plain").status_code, 400)
        self.assertEqual(self.post("[1, 2]").status_code, 400)
        self.assertEqual(Visit.objects.exclude(visitor_id="").count(), 0)

    def test_a_big_body_is_refused(self):
        self.assertEqual(self.post({"visitor_id": GOOD_ID, "junk": "x" * 1000}).status_code, 400)

    def test_only_post_is_allowed(self):
        self.assertEqual(self.client.get("/api/visitors/ping/").status_code, 405)

    def test_an_ordinary_request_has_no_id(self):
        self.client.get("/api/matches/")
        self.assertEqual(Visit.objects.get().visitor_id, "")


class BotFilterTests(TestCase):
    def test_robots_are_told_from_browsers_by_the_user_agent(self):
        robots = [
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; bingbot/2.0)",
            "UptimeRobot/2.0",
            "curl/8.4.0",
            "python-requests/2.32",
            "facebookexternalhit/1.1",
            "WhatsApp/2.23",
            "Mozilla/5.0 (X11; Linux x86_64) HeadlessChrome/120.0",
            "Go-http-client/2.0",
        ]
        people = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120.0 "
            "Mobile Safari/537.36",
            "",
        ]
        for agent in robots + people:
            Visit.objects.create(path="/api/a/", method="GET", status_code=200, user_agent=agent)
        self.assertEqual(
            sorted(bot_visits(Visit.objects.all()).values_list("user_agent", flat=True)),
            sorted(robots),
        )
        self.assertEqual(human_visits(Visit.objects.all()).count(), len(people))


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

    def ping(self, visitor_id, ip="1.1.1.1", agent="Mozilla/5.0 Chrome/120", **extra):
        return Visit.objects.create(
            ip=ip,
            path="/api/visitors/ping/",
            method="POST",
            status_code=204,
            visitor_id=visitor_id,
            user_agent=agent,
            **extra,
        )

    def test_visitors_are_counted_by_id_not_by_ip(self):
        a, b = GOOD_ID, "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        self.ping(a, ip="1.1.1.1")
        self.ping(a, ip="2.2.2.2")  # the same browser on another network: one visitor
        self.ping(b, ip="1.1.1.1")  # another browser on the same network: another visitor
        response = self.client.get(reverse("admin:visitors_visit_stats"))
        totals = dict(response.context["totals"])
        self.assertEqual(totals["Відвідувачів за добу"], 2)
        self.assertEqual(totals["Відвідувачів за 7 днів"], 2)
        self.assertEqual(totals["Відвідувачів усього"], 2)
        self.assertEqual(response.context["per_day"][0]["visitors"], 2)

    def test_pings_are_not_counted_as_requests(self):
        self.ping(GOOD_ID)
        self.visit("3.3.3.3")
        response = self.client.get(reverse("admin:visitors_visit_stats"))
        self.assertEqual(dict(response.context["totals"])["Запитів за добу"], 1)
        self.assertEqual([row["label"] for row in response.context["paths"]], ["/api/matches/"])

    def test_robots_are_not_counted_but_are_reported_separately(self):
        self.ping(GOOD_ID, agent="Googlebot/2.1")
        self.ping("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", agent="Chrome/120")
        Visit.objects.create(
            ip="9.9.9.9", path="/api/matches/", method="GET", status_code=200, user_agent="curl/8"
        )
        self.visit("4.4.4.4")
        totals = dict(self.client.get(reverse("admin:visitors_visit_stats")).context["totals"])
        self.assertEqual(totals["Відвідувачів за добу"], 1)
        self.assertEqual(totals["Запитів за добу"], 1)
        self.assertEqual(totals["Унікальних IP за добу"], 1)
        self.assertEqual(totals["Запитів від ботів за добу"], 2)

    def test_a_ping_without_an_id_is_not_a_visitor(self):
        self.ping("")
        totals = dict(self.client.get(reverse("admin:visitors_visit_stats")).context["totals"])
        self.assertEqual(totals["Відвідувачів усього"], 0)
