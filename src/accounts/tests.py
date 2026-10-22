import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, RequestFactory, TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from .admin import UserAdmin, can_manage_admin_target
from .email_codes import MAX_ATTEMPTS, MAX_CODES_PER_HOUR
from .models import EmailCode, GroupChatMessage, Profile
from .services import assign_study_group_from_email
from .utils import get_student_record_book_number, parse_volsu_student_email


class AdminGrantTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = UserAdmin(User, self.site)
        self.factory = RequestFactory()

    def create_user(self, username, *, admin=False, primary=False, granted_by=None):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="password",
            is_staff=admin,
            is_superuser=admin,
        )
        profile = user.profile
        profile.role = "admin" if admin else "student"
        profile.is_primary_admin = primary
        profile.admin_granted_by = granted_by
        profile.save(update_fields=["role", "is_primary_admin", "admin_granted_by"])
        return user

    def request_for(self, user):
        request = self.factory.post("/admin/auth/user/")
        request.user = user
        return request

    def test_primary_admin_can_manage_secondary_admin(self):
        primary = self.create_user("primary", admin=True, primary=True)
        secondary = self.create_user("secondary", admin=True, granted_by=primary)

        self.assertTrue(can_manage_admin_target(primary, secondary))

    def test_granting_admin_can_manage_their_grantee(self):
        primary = self.create_user("primary", admin=True, primary=True)
        grantor = self.create_user("grantor", admin=True, granted_by=primary)
        grantee = self.create_user("grantee", admin=True, granted_by=grantor)

        self.assertTrue(can_manage_admin_target(grantor, grantee))

    def test_unrelated_admin_cannot_manage_other_admin(self):
        primary = self.create_user("primary", admin=True, primary=True)
        grantor = self.create_user("grantor", admin=True, granted_by=primary)
        grantee = self.create_user("grantee", admin=True, granted_by=grantor)
        unrelated = self.create_user("unrelated", admin=True, granted_by=primary)

        self.assertFalse(can_manage_admin_target(unrelated, grantee))

    def test_make_admin_records_grantor_and_gives_full_permissions(self):
        primary = self.create_user("primary", admin=True, primary=True)
        user = self.create_user("student")

        with patch.object(self.admin, "message_user"):
            self.admin.make_admin(self.request_for(primary), User.objects.filter(pk=user.pk))

        user.refresh_from_db()
        profile = Profile.objects.get(user=user)

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(profile.role, "admin")
        self.assertEqual(profile.admin_granted_by, primary)

    def test_remove_admin_revokes_role_and_permissions_for_allowed_grantor(self):
        primary = self.create_user("primary", admin=True, primary=True)
        grantee = self.create_user("grantee", admin=True, granted_by=primary)

        with patch.object(self.admin, "message_user"):
            self.admin.remove_admin(self.request_for(primary), User.objects.filter(pk=grantee.pk))

        grantee.refresh_from_db()
        profile = Profile.objects.get(user=grantee)

        self.assertFalse(grantee.is_staff)
        self.assertFalse(grantee.is_superuser)
        self.assertEqual(profile.role, "student")
        self.assertIsNone(profile.admin_granted_by)

    def test_remove_admin_skips_unrelated_admin(self):
        primary = self.create_user("primary", admin=True, primary=True)
        grantee = self.create_user("grantee", admin=True, granted_by=primary)
        unrelated = self.create_user("unrelated", admin=True, granted_by=primary)

        with patch.object(self.admin, "message_user"):
            self.admin.remove_admin(self.request_for(unrelated), User.objects.filter(pk=grantee.pk))

        grantee.refresh_from_db()
        profile = Profile.objects.get(user=grantee)

        self.assertTrue(grantee.is_staff)
        self.assertTrue(grantee.is_superuser)
        self.assertEqual(profile.role, "admin")


class StudentRecordBookNumberTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = UserAdmin(User, self.site)

    def test_extracts_record_book_number_from_volsu_email(self):
        self.assertEqual(
            get_student_record_book_number("pmib-231_634292@volsu.ru"),
            "634292",
        )

    def test_returns_dash_for_non_volsu_or_invalid_email(self):
        self.assertEqual(get_student_record_book_number("student@example.com"), "-")
        self.assertEqual(get_student_record_book_number("pmib-231@volsu.ru"), "-")
        self.assertEqual(get_student_record_book_number("pmib-231_test@volsu.ru"), "-")

    def test_admin_column_returns_dash_for_non_students(self):
        user = User.objects.create_user(
            username="teacher",
            email="pmib-231_634292@volsu.ru",
            password="password",
        )
        user.profile.role = "teacher"
        user.profile.save(update_fields=["role"])

        self.assertEqual(self.admin.get_record_book_number(user), "-")


class ProfilePasswordChangeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="old-password",
        )

    def test_user_can_change_own_password(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("change_profile_password"), {
            "password": "new-password",
            "password_repeat": "new-password",
        })

        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_password_change_rejects_mismatch(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("change_profile_password"), {
            "password": "new-password",
            "password_repeat": "other-password",
        })

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-password"))
        self.assertContains(response, "Пароли не совпадают.")

    def test_password_change_rejects_short_password(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("change_profile_password"), {
            "password": "12345678",
            "password_repeat": "12345678",
        })

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-password"))
        self.assertContains(response, "Пароль должен быть длиннее 8 символов.")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def code_from_last_email():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def wrong_code(code):
    return f"{(int(code) + 1) % 1000000:06d}"


class EmailCodeLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student",
            email="student@volsu.ru",
            password="correct-password",
        )

    def send_login_code(self, client=None):
        return (client or self.client).post(reverse("send_login_code"), {"email": self.user.email})

    def verify_login(self, code, client=None):
        return (client or self.client).post(reverse("verify_login_code"), {"email": self.user.email, "code": code})

    def allow_resend(self):
        EmailCode.objects.update(created_at=timezone.now() - timedelta(minutes=2))

    def test_code_is_burned_after_max_wrong_attempts(self):
        self.send_login_code()
        code = code_from_last_email()

        for attempt in range(MAX_ATTEMPTS):
            response = self.verify_login(wrong_code(code))
            self.assertEqual(response.status_code, 400)

        self.assertIn("Слишком много неверных попыток", response.json()["error"])
        response = self.verify_login(code)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_attempts_are_counted_across_sessions(self):
        self.send_login_code()
        code = code_from_last_email()

        for attempt in range(MAX_ATTEMPTS):
            self.verify_login(wrong_code(code), client=Client())

        response = self.verify_login(code)
        self.assertEqual(response.status_code, 400)

    def test_wrong_code_reports_remaining_attempts(self):
        self.send_login_code()

        response = self.verify_login(wrong_code(code_from_last_email()))

        self.assertIn(f"Осталось попыток: {MAX_ATTEMPTS - 1}", response.json()["error"])

    def test_code_cannot_be_reused(self):
        self.send_login_code()
        code = code_from_last_email()
        self.assertEqual(self.verify_login(code).status_code, 200)

        response = self.verify_login(code, client=Client())

        self.assertEqual(response.status_code, 400)

    def test_new_code_invalidates_previous_one(self):
        self.send_login_code()
        old_code = code_from_last_email()
        self.allow_resend()
        self.send_login_code()
        new_code = code_from_last_email()

        if old_code != new_code:
            self.assertEqual(self.verify_login(old_code).status_code, 400)
        self.assertEqual(self.verify_login(new_code).status_code, 200)

    def test_expired_code_is_rejected(self):
        self.send_login_code()
        EmailCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        response = self.verify_login(code_from_last_email())

        self.assertEqual(response.status_code, 400)

    def test_resend_cooldown_applies_to_every_session(self):
        self.send_login_code()

        response = self.send_login_code(client=Client())

        self.assertEqual(response.status_code, 429)
        self.assertGreater(response.json()["retry_after"], 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_hourly_limit_per_email(self):
        for number in range(MAX_CODES_PER_HOUR):
            self.assertEqual(self.send_login_code().status_code, 200)
            self.allow_resend()

        response = self.send_login_code(client=Client())

        self.assertEqual(response.status_code, 429)
        self.assertIn("Слишком много запросов", response.json()["error"])

    def test_failed_email_does_not_count_against_limits(self):
        with patch("accounts.views.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("accounts.views", level="ERROR"):
            response = self.send_login_code()

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("smtp down", response.json()["error"])
        self.assertFalse(EmailCode.objects.exists())
        self.assertEqual(self.send_login_code().status_code, 200)

    def test_registration_requires_verified_email(self):
        email = "pmib-231_123456@volsu.ru"
        form = {
            "full_name": "Новый Студент",
            "email": email,
            "password1": "Very-strong-pass-42",
            "password2": "Very-strong-pass-42",
        }

        response = self.client.post(reverse("register"), form)
        self.assertContains(response, "Подтвердите почту кодом")

        self.client.post(reverse("send_registration_code"), {"email": email})
        code = code_from_last_email()
        verify = self.client.post(reverse("verify_registration_code"), {"email": email, "code": code})
        self.assertEqual(verify.status_code, 200)

        response = self.client.post(reverse("register"), form)
        self.assertRedirects(response, "/")
        self.assertTrue(User.objects.filter(email=email).exists())

    def test_registration_code_attempts_are_limited(self):
        email = "pmib-231_123456@volsu.ru"
        self.client.post(reverse("send_registration_code"), {"email": email})
        code = code_from_last_email()

        for attempt in range(MAX_ATTEMPTS):
            Client().post(reverse("verify_registration_code"), {"email": email, "code": wrong_code(code)})

        response = self.client.post(reverse("verify_registration_code"), {"email": email, "code": code})
        self.assertEqual(response.status_code, 400)

    def test_verified_flag_is_bound_to_email(self):
        email = "pmib-231_123456@volsu.ru"
        self.client.post(reverse("send_registration_code"), {"email": email})
        self.client.post(reverse("verify_registration_code"), {"email": email, "code": code_from_last_email()})

        response = self.client.post(reverse("register"), {
            "full_name": "Чужая почта",
            "email": "pmib-231_999999@volsu.ru",
            "password1": "Very-strong-pass-42",
            "password2": "Very-strong-pass-42",
        })

        self.assertContains(response, "Подтвердите почту кодом")


class LoginCodeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="correct-password",
        )

    def test_login_shows_register_prompt_for_unknown_email(self):
        response = self.client.post("/login/", {
            "username": "missing@example.com",
            "password": "password",
        })

        self.assertContains(response, "Пользователь с такой почтой не зарегистрирован")
        self.assertContains(response, "Зарегистрироваться")

    def test_login_shows_email_code_prompt_for_wrong_password(self):
        response = self.client.post("/login/", {
            "username": self.user.email,
            "password": "wrong-password",
        })

        self.assertContains(response, "Неправильный пароль! Забыли?")
        self.assertContains(response, "войти по коду с почты")

    def test_send_login_code_sends_six_digit_code(self):
        response = self.client.post(reverse("send_login_code"), {"email": self.user.email})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        code = code_from_last_email()
        self.assertEqual(len(code), 6)
        self.assertNotIn(code, str(dict(self.client.session)))
        record = EmailCode.objects.get()
        self.assertEqual(len(record.code_hash), 64)
        self.assertNotEqual(record.code_hash, code)

    def test_verify_login_code_logs_user_in(self):
        self.client.post(reverse("send_login_code"), {"email": self.user.email})
        code = code_from_last_email()

        response = self.client.post(reverse("verify_login_code"), {
            "email": self.user.email,
            "code": code,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redirect_url"], "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)


class StudyGroupChatTests(TestCase):
    def setUp(self):
        self.client = Client()

    def create_student(self, username, email):
        user = User.objects.create_user(
            username=username,
            email=email,
            password="password",
        )
        user.profile.full_name = f"{username.title()} Test"
        user.profile.save(update_fields=["full_name"])
        assign_study_group_from_email(user.profile)
        return user

    def test_parses_study_group_from_volsu_email(self):
        student_data = parse_volsu_student_email("pmib-231_634292@volsu.ru")

        self.assertEqual(student_data["group_code"], "pmib-231")
        self.assertEqual(student_data["group_name"], "ПМИб-231")
        self.assertEqual(student_data["record_book_number"], "634292")

    def test_assigns_students_with_same_email_group_to_same_study_group(self):
        first = self.create_student("first", "pmib-231_111111@volsu.ru")
        second = self.create_student("second", "pmib-231_222222@volsu.ru")

        first.profile.refresh_from_db()
        second.profile.refresh_from_db()

        self.assertIsNotNone(first.profile.study_group)
        self.assertEqual(first.profile.study_group, second.profile.study_group)
        self.assertEqual(first.profile.study_group.display_name, "ПМИб-231")

    def test_group_chat_uses_first_name_and_last_initial_for_member_list(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        user.profile.full_name = "Иван Попов Сергеевич"
        user.profile.save(update_fields=["full_name"])

        self.client.force_login(user)
        response = self.client.get(reverse("group_chat"))

        self.assertContains(response, "Иван П.")
        self.assertEqual(user.profile.short_name, "Иван П.С.")

    def test_group_chat_online_count_excludes_current_user(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        user.profile.last_seen_at = timezone.now()
        user.profile.save(update_fields=["last_seen_at"])
        self.client.force_login(user)

        response = self.client.get(
            reverse("group_chat_updates"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.json()["online_count"], 0)
        self.assertIn(user.id, response.json()["online_member_ids"])

    def test_group_chat_creates_message_for_current_student_group(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        self.client.force_login(user)

        response = self.client.post(reverse("group_chat"), {"text": "Привет, группа!"})

        self.assertRedirects(response, reverse("group_chat"))
        message = GroupChatMessage.objects.get()
        self.assertEqual(message.author, user)
        self.assertEqual(message.study_group, user.profile.study_group)
        self.assertEqual(message.text, "Привет, группа!")
        self.assertTrue(message.read_by.filter(id=user.id).exists())

    def test_group_chat_creates_reply(self):
        first = self.create_student("first", "pmib-231_111111@volsu.ru")
        second = self.create_student("second", "pmib-231_222222@volsu.ru")
        original = GroupChatMessage.objects.create(
            study_group=first.profile.study_group,
            author=first,
            text="Первое сообщение",
        )
        self.client.force_login(second)

        response = self.client.post(reverse("group_chat"), {
            "text": "Ответ",
            "reply_to": original.id,
        })

        self.assertRedirects(response, reverse("group_chat"))
        reply = GroupChatMessage.objects.get(text="Ответ")
        self.assertEqual(reply.reply_to, original)

    def test_group_chat_marks_visible_messages_as_read(self):
        first = self.create_student("first", "pmib-231_111111@volsu.ru")
        second = self.create_student("second", "pmib-231_222222@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=first.profile.study_group,
            author=first,
            text="Нужно прочитать",
        )
        self.client.force_login(second)

        self.client.get(reverse("group_chat"))

        self.assertTrue(message.read_by.filter(id=second.id).exists())

    def test_group_chat_does_not_override_django_messages_context(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        GroupChatMessage.objects.create(
            study_group=user.profile.study_group,
            author=user,
            text="Сообщение без alert сверху",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("group_chat"))

        self.assertContains(response, "Сообщение без alert сверху")
        self.assertNotContains(response, "alert-success")

    def test_author_can_edit_own_group_chat_message(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=user.profile.study_group,
            author=user,
            text="Старый текст",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("edit_group_chat_message", kwargs={"message_id": message.id}),
            {"text": "Новый текст"},
        )

        self.assertRedirects(response, reverse("group_chat"))
        message.refresh_from_db()
        self.assertEqual(message.text, "Новый текст")
        self.assertIsNotNone(message.edited_at)

    def test_empty_edit_returns_errors_for_ajax_and_keeps_text(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=user.profile.study_group,
            author=user,
            text="Старый текст",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("edit_group_chat_message", kwargs={"message_id": message.id}),
            {"text": "   "},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json()["errors"])
        message.refresh_from_db()
        self.assertEqual(message.text, "Старый текст")
        self.assertIsNone(message.edited_at)

    def test_message_markup_escapes_author_name(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        user.profile.full_name = "<b>Иван</b>"
        user.profile.save(update_fields=["full_name"])
        GroupChatMessage.objects.create(study_group=user.profile.study_group, author=user, text="<i>текст</i>")
        self.client.force_login(user)

        response = self.client.get(reverse("group_chat_updates"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        html = response.json()["html"]
        self.assertNotIn("<b>Иван</b>", html)
        self.assertNotIn("<i>текст</i>", html)
        self.assertIn("&lt;i&gt;текст&lt;/i&gt;", html)

    def test_other_group_member_cannot_edit_message(self):
        author = self.create_student("first", "pmib-231_111111@volsu.ru")
        other = self.create_student("second", "pmib-231_222222@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=author.profile.study_group,
            author=author,
            text="Нельзя редактировать",
        )
        self.client.force_login(other)

        response = self.client.post(
            reverse("edit_group_chat_message", kwargs={"message_id": message.id}),
            {"text": "Попытка"},
        )

        self.assertEqual(response.status_code, 404)
        message.refresh_from_db()
        self.assertEqual(message.text, "Нельзя редактировать")

    def test_user_can_hide_message_for_self(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=user.profile.study_group,
            author=user,
            text="Удалить",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("delete_group_chat_message", kwargs={"message_id": message.id}),
            {"scope": "me"},
        )

        self.assertRedirects(response, reverse("group_chat"))
        message.refresh_from_db()
        self.assertFalse(message.is_deleted)
        self.assertTrue(message.hidden_for.filter(id=user.id).exists())

    def test_author_can_delete_message_for_everyone(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=user.profile.study_group,
            author=user,
            text="Удалить",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("delete_group_chat_message", kwargs={"message_id": message.id}),
            {"scope": "all"},
        )

        self.assertRedirects(response, reverse("group_chat"))
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)
        self.assertEqual(message.text, "")
        self.assertIsNotNone(message.deleted_at)

    def test_deleted_for_everyone_message_is_not_rendered_in_chat(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=user.profile.study_group,
            author=user,
            text="Исчезающее сообщение",
        )
        message.mark_deleted()
        self.client.force_login(user)

        response = self.client.get(reverse("group_chat"))

        self.assertNotContains(response, "Исчезающее сообщение")
        self.assertNotContains(response, "Сообщение удалено")

    def test_group_chat_readers_endpoint_returns_readers(self):
        author = self.create_student("first", "pmib-231_111111@volsu.ru")
        reader = self.create_student("second", "pmib-231_222222@volsu.ru")
        message = GroupChatMessage.objects.create(
            study_group=author.profile.study_group,
            author=author,
            text="Прочитано",
        )
        message.read_by.add(author, reader)
        self.client.force_login(author)

        response = self.client.get(reverse("group_chat_readers", kwargs={"message_id": message.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["readers"][0]["name"], reader.profile.short_name)
