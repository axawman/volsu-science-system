import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from meetings.models import Meeting


class CalendarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("author", password="password")

    def aware(self, *args):
        return timezone.make_aware(datetime(*args))

    def test_calendar_page_renders(self):
        response = self.client.get(reverse("calendar"))

        self.assertContains(response, "Календарь")

    def test_items_are_limited_to_requested_month(self):
        Meeting.objects.create(title="Встреча в марте", start_at=self.aware(2026, 3, 31, 23, 30), created_by=self.user)
        Event.objects.create(title="Событие в апреле", event_date=self.aware(2026, 4, 1, 0, 0), created_by=self.user)
        Event.objects.create(title="Событие в мае", event_date=self.aware(2026, 5, 1, 0, 0), created_by=self.user)

        response = self.client.get(reverse("calendar_items"), {"month": "2026-04"})

        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual([item["title"] for item in items], ["Событие в апреле"])
        self.assertEqual(items[0]["date"], "2026-04-01")
        self.assertEqual(items[0]["type"], "event")

    def test_december_includes_last_day_of_year(self):
        Meeting.objects.create(title="Новогодняя", start_at=self.aware(2026, 12, 31, 18, 0), created_by=self.user)

        response = self.client.get(reverse("calendar_items"), {"month": "2026-12"})

        self.assertEqual([item["title"] for item in response.json()["items"]], ["Новогодняя"])

    def test_invalid_month_is_rejected(self):
        response = self.client.get(reverse("calendar_items"), {"month": "april"})

        self.assertEqual(response.status_code, 400)

    def test_home_no_longer_embeds_calendar(self):
        Meeting.objects.create(title="Прошедшая встреча", start_at=self.aware(2020, 1, 1, 12, 0), created_by=self.user)

        response = self.client.get(reverse("home"))

        self.assertNotIn("calendar_items", response.context)
        self.assertNotContains(response, "Прошедшая встреча")
        self.assertContains(response, reverse("calendar"))


@override_settings(DEBUG=False)
class PublicMediaTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        for name in ("profile_photos/avatar.jpg", "work_versions/secret.pdf"):
            path = Path(self.media_root) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"content")

    def get(self, url):
        with override_settings(MEDIA_ROOT=self.media_root):
            return self.client.get(url)

    def test_profile_photo_is_served(self):
        response = self.get("/media/profile_photos/avatar.jpg")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"content")

    def test_work_files_are_not_served_directly(self):
        response = self.get("/media/work_versions/secret.pdf")

        self.assertEqual(response.status_code, 404)

    def test_path_traversal_is_rejected(self):
        for url in (
            "/media/profile_photos/../work_versions/secret.pdf",
            "/media/profile_photos/%2e%2e/work_versions/secret.pdf",
            "/media/profile_photos/x/../../work_versions/secret.pdf",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.get(url).status_code, 404)
