from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from .admin import UserAdmin, can_manage_admin_target
from .models import GroupChatMessage, Profile
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

    def test_group_chat_creates_message_for_current_student_group(self):
        user = self.create_student("first", "pmib-231_111111@volsu.ru")
        self.client.force_login(user)

        response = self.client.post(reverse("group_chat"), {"text": "Привет, группа!"})

        self.assertRedirects(response, reverse("group_chat"))
        message = GroupChatMessage.objects.get()
        self.assertEqual(message.author, user)
        self.assertEqual(message.study_group, user.profile.study_group)
        self.assertEqual(message.text, "Привет, группа!")
