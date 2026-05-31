from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from .admin import UserAdmin, can_manage_admin_target, get_student_record_book_number
from .models import Profile


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
