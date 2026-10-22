from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import PersonalEvent
from .reminders import send_due_reminders


class PersonalEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student", password="password")
        self.other = User.objects.create_user("other", password="password")
        self.client.force_login(self.user)

    def create_event(self, owner=None, starts_at=None, **kwargs):
        return PersonalEvent.objects.create(
            owner=owner or self.user,
            title=kwargs.pop("title", "Сдать отчёт"),
            starts_at=starts_at or timezone.now() + timedelta(days=2),
            **kwargs,
        )

    def form_data(self, starts_at, **overrides):
        local_start = timezone.localtime(starts_at)
        data = {
            "title": "Консультация",
            "date": local_start.strftime("%Y-%m-%d"),
            "time": local_start.strftime("%H:%M"),
            "remind_before": "",
            "description": "",
        }
        data.update(overrides)
        return data

    def test_remind_at_is_calculated_from_start(self):
        starts_at = timezone.now() + timedelta(days=3)
        event = self.create_event(starts_at=starts_at, remind_before=60)

        self.assertEqual(event.remind_at, starts_at - timedelta(minutes=60))

        event.remind_before = None
        event.save()
        self.assertIsNone(event.remind_at)

    def test_create_personal_event(self):
        starts_at = (timezone.now() + timedelta(days=5)).replace(second=0, microsecond=0)

        response = self.client.post(
            reverse("create_personal_event"),
            self.form_data(starts_at, remind_before="1440"),
        )

        self.assertEqual(response.status_code, 200)
        event = PersonalEvent.objects.get()
        self.assertEqual(event.owner, self.user)
        self.assertEqual(event.starts_at, starts_at)
        self.assertEqual(event.remind_at, starts_at - timedelta(days=1))
        self.assertEqual(response.json()["item"]["type"], "personal")
        self.assertIsNone(response.json()["reminder"])

    def test_create_returns_reminder_due_within_a_day(self):
        starts_at = (timezone.now() + timedelta(hours=3)).replace(second=0, microsecond=0)

        response = self.client.post(
            reverse("create_personal_event"),
            self.form_data(starts_at, remind_before="60"),
        )

        self.assertEqual(response.json()["reminder"]["title"], "Консультация")

    def test_reminder_in_the_past_is_rejected(self):
        starts_at = timezone.now() + timedelta(minutes=30)

        response = self.client.post(
            reverse("create_personal_event"),
            self.form_data(starts_at, remind_before="1440"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("remind_before", response.json()["errors"])
        self.assertFalse(PersonalEvent.objects.exists())

    def test_past_event_without_reminder_is_allowed(self):
        starts_at = timezone.now() - timedelta(days=10)

        response = self.client.post(reverse("create_personal_event"), self.form_data(starts_at))

        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_create(self):
        self.client.logout()

        response = self.client.post(
            reverse("create_personal_event"),
            self.form_data(timezone.now() + timedelta(days=1)),
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(PersonalEvent.objects.exists())

    def test_cannot_edit_or_delete_other_users_event(self):
        event = self.create_event(owner=self.other)

        update = self.client.post(
            reverse("update_personal_event", kwargs={"event_id": event.id}),
            self.form_data(event.starts_at, title="Взлом"),
        )
        delete = self.client.post(reverse("delete_personal_event", kwargs={"event_id": event.id}))
        dismiss = self.client.post(reverse("dismiss_personal_reminder", kwargs={"event_id": event.id}))

        self.assertEqual(update.status_code, 404)
        self.assertEqual(delete.status_code, 404)
        self.assertEqual(dismiss.status_code, 404)
        event.refresh_from_db()
        self.assertEqual(event.title, "Сдать отчёт")

    def test_update_reschedules_and_resets_dismissed_reminder(self):
        event = self.create_event(remind_before=60, reminder_dismissed_at=timezone.now())
        new_start = (event.starts_at + timedelta(days=1)).replace(second=0, microsecond=0)

        response = self.client.post(
            reverse("update_personal_event", kwargs={"event_id": event.id}),
            self.form_data(new_start, title=event.title, remind_before="60"),
        )

        self.assertEqual(response.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.starts_at, new_start)
        self.assertEqual(event.remind_at, new_start - timedelta(hours=1))
        self.assertIsNone(event.reminder_dismissed_at)

    def test_renaming_keeps_dismissed_reminder(self):
        dismissed_at = timezone.now()
        event = self.create_event(remind_before=60, reminder_dismissed_at=dismissed_at)

        self.client.post(
            reverse("update_personal_event", kwargs={"event_id": event.id}),
            self.form_data(event.starts_at, title="Новое название", remind_before="60"),
        )

        event.refresh_from_db()
        self.assertEqual(event.title, "Новое название")
        self.assertEqual(event.reminder_dismissed_at, dismissed_at)

    def test_delete_personal_event(self):
        event = self.create_event()

        response = self.client.post(reverse("delete_personal_event", kwargs={"event_id": event.id}))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(PersonalEvent.objects.exists())

    def test_pending_reminders_are_shown_only_to_owner(self):
        self.create_event(title="Моё", starts_at=timezone.now() + timedelta(minutes=30), remind_before=60)
        self.create_event(owner=self.other, title="Чужое", starts_at=timezone.now() + timedelta(minutes=30), remind_before=60)

        response = self.client.get(reverse("home"))

        titles = [reminder["title"] for reminder in response.context["personal_reminders"]]
        self.assertEqual(titles, ["Моё"])

    def test_far_and_dismissed_reminders_are_not_pending(self):
        self.create_event(title="Через месяц", starts_at=timezone.now() + timedelta(days=30), remind_before=60)
        dismissed = self.create_event(title="Скрытое", starts_at=timezone.now() + timedelta(minutes=30), remind_before=60)

        self.client.post(reverse("dismiss_personal_reminder", kwargs={"event_id": dismissed.id}))
        response = self.client.get(reverse("home"))

        self.assertEqual(response.context["personal_reminders"], [])

    def test_calendar_items_include_only_own_personal_events(self):
        starts_at = timezone.make_aware(datetime(2026, 4, 10, 12, 0))
        self.create_event(title="Моё", starts_at=starts_at)
        self.create_event(owner=self.other, title="Чужое", starts_at=starts_at)

        response = self.client.get(reverse("calendar_items"), {"month": "2026-04"})
        titles = [item["title"] for item in response.json()["items"]]

        self.assertEqual(titles, ["Моё"])

        self.client.logout()
        response = self.client.get(reverse("calendar_items"), {"month": "2026-04"})
        self.assertEqual(response.json()["items"], [])

    def test_upcoming_activity_includes_own_personal_events(self):
        self.create_event(title="Моё ближайшее")
        self.create_event(owner=self.other, title="Чужое ближайшее")

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Моё ближайшее")
        self.assertNotContains(response, "Чужое ближайшее")


class ReminderEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student", email="student@volsu.ru", password="password")
        self.now = timezone.now()

    def create_event(self, starts_in, remind_before=60, **kwargs):
        return PersonalEvent.objects.create(
            owner=kwargs.pop("owner", self.user),
            title=kwargs.pop("title", "Защита курсовой"),
            description=kwargs.pop("description", "Аудитория 4-01"),
            starts_at=self.now + starts_in,
            remind_before=remind_before,
            **kwargs,
        )

    def test_due_reminder_is_emailed_once(self):
        event = self.create_event(timedelta(minutes=30))

        self.assertEqual(send_due_reminders(self.now), (1, 0))
        self.assertEqual(send_due_reminders(self.now), (0, 0))

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["student@volsu.ru"])
        self.assertEqual(message.subject, "Напоминание: Защита курсовой")
        self.assertIn(timezone.localtime(event.starts_at).strftime("%d.%m.%Y в %H:%M"), message.body)
        self.assertIn("Аудитория 4-01", message.body)
        self.assertIn("/calendar/", message.body)
        event.refresh_from_db()
        self.assertIsNotNone(event.reminder_emailed_at)

    def test_reminder_is_not_sent_before_its_time(self):
        self.create_event(timedelta(hours=3), remind_before=60)

        self.assertEqual(send_due_reminders(self.now), (0, 0))
        self.assertEqual(send_due_reminders(self.now + timedelta(hours=2, minutes=1)), (1, 0))

    def test_entries_without_reminder_or_long_past_are_skipped(self):
        self.create_event(timedelta(minutes=30), remind_before=None)
        self.create_event(-timedelta(days=3), remind_before=60)

        self.assertEqual(send_due_reminders(self.now), (0, 0))
        self.assertEqual(mail.outbox, [])

    def test_inactive_users_and_users_without_email_are_skipped(self):
        inactive = User.objects.create_user("gone", email="gone@volsu.ru", is_active=False)
        no_email = User.objects.create_user("noemail", email="")
        self.create_event(timedelta(minutes=30), owner=inactive)
        self.create_event(timedelta(minutes=30), owner=no_email)

        self.assertEqual(send_due_reminders(self.now), (0, 0))

    def test_failed_email_is_retried_next_run(self):
        event = self.create_event(timedelta(minutes=30))

        with patch("events.reminders.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("events.reminders", level="ERROR"):
            self.assertEqual(send_due_reminders(self.now), (0, 1))

        event.refresh_from_db()
        self.assertIsNone(event.reminder_emailed_at)
        self.assertEqual(send_due_reminders(self.now), (1, 0))

    def test_changing_time_sends_reminder_again(self):
        event = self.create_event(timedelta(minutes=30))
        send_due_reminders(self.now)
        self.client.force_login(self.user)
        new_start = timezone.localtime(timezone.now() + timedelta(days=2)).replace(second=0, microsecond=0)

        self.client.post(reverse("update_personal_event", kwargs={"event_id": event.id}), {
            "title": event.title,
            "date": new_start.strftime("%Y-%m-%d"),
            "time": new_start.strftime("%H:%M"),
            "remind_before": "60",
            "description": "",
        })

        event.refresh_from_db()
        self.assertIsNone(event.reminder_emailed_at)
        self.assertEqual(send_due_reminders(new_start - timedelta(minutes=59)), (1, 0))

    def test_renaming_does_not_resend(self):
        event = self.create_event(timedelta(minutes=30))
        send_due_reminders(self.now)
        self.client.force_login(self.user)
        local_start = timezone.localtime(event.starts_at)

        self.client.post(reverse("update_personal_event", kwargs={"event_id": event.id}), {
            "title": "Новое название",
            "date": local_start.strftime("%Y-%m-%d"),
            "time": local_start.strftime("%H:%M"),
            "remind_before": "60",
            "description": "",
        })

        self.assertEqual(send_due_reminders(self.now), (0, 0))

    def test_command_runs_once(self):
        self.create_event(timedelta(minutes=30))
        out = StringIO()

        call_command("send_reminders", stdout=out)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("отправлено: 1", out.getvalue())
