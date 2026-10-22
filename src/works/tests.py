import shutil
import tempfile
from itertools import product

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Work, WorkSection, WorkVersion, WorkVersionFile


class WorkDetailMathTests(TestCase):
    def setUp(self):
        author = User.objects.create_user("author", password="password")
        self.work = Work.objects.create(
            title="Работа с формулами",
            content="$\\href{javascript:alert(1)}{x}$",
            author=author,
            status="published",
            visibility="public",
        )

    def test_mathjax_is_pinned_and_loaded_with_safe_extension(self):
        response = self.client.get(reverse("work_detail", kwargs={"work_id": self.work.id}))

        # ui/safe блокирует javascript:-ссылки в \href и опасные стили в \style
        self.assertContains(response, "load: ['ui/safe']")
        self.assertContains(response, "mathjax@3.2.2/")
        self.assertNotContains(response, "mathjax@3/")
        # Автоматическая обработка всей страницы задела бы и комментарии
        self.assertContains(response, "typeset: false")

    def test_description_is_passed_as_json_not_html(self):
        response = self.client.get(reverse("work_detail", kwargs={"work_id": self.work.id}))

        self.assertContains(response, 'id="work-content-data"')
        self.assertNotContains(response, '<a href="javascript:')


class WorkAccessMatrixTests(TestCase):
    """Кто что видит: статус × видимость × зритель. Одно правило для страницы, файлов, списков и поиска."""

    STATUSES = ("draft", "published")
    VISIBILITIES = ("private", "public")
    VIEWERS = ("anonymous", "other", "author", "admin")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.users = {
            "author": User.objects.create_user("author", password="password"),
            "other": User.objects.create_user("other", password="password"),
            "admin": User.objects.create_user("admin", password="password", is_staff=True, is_superuser=True),
        }
        self.section = WorkSection.objects.create(name="Раздел")
        self.works = {}
        for status, visibility in product(self.STATUSES, self.VISIBILITIES):
            work = Work.objects.create(
                title=f"Работа {status} {visibility}",
                content=f"секрет-{status}-{visibility}",
                author=self.users["author"],
                section=self.section,
                status=status,
                visibility=visibility,
            )
            version = WorkVersion.objects.create(work=work, version_number=1, uploaded_by=self.users["author"])
            work_file = WorkVersionFile.objects.create(
                version=version,
                file=SimpleUploadedFile(f"{status}-{visibility}.txt", b"file-content"),
                original_name=f"{status}-{visibility}.txt",
            )
            self.works[(status, visibility)] = (work, version, work_file)

    def login(self, viewer):
        self.client.logout()
        if viewer != "anonymous":
            self.client.force_login(self.users[viewer])

    @staticmethod
    def expected_visible(status, visibility, viewer):
        return (status, visibility) == ("published", "public") or viewer in ("author", "admin")

    def test_matrix(self):
        for viewer, (status, visibility) in product(self.VIEWERS, self.works):
            work, version, work_file = self.works[(status, visibility)]
            visible = self.expected_visible(status, visibility, viewer)
            self.login(viewer)

            with self.subTest(viewer=viewer, status=status, visibility=visibility, place="detail"):
                response = self.client.get(reverse("work_detail", kwargs={"work_id": work.id}))
                self.assertEqual(response.status_code, 200 if visible else 403)

            with self.subTest(viewer=viewer, status=status, visibility=visibility, place="file"):
                response = self.client.get(reverse("download_version_file", kwargs={
                    "work_id": work.id, "version_id": version.id, "file_id": work_file.id,
                }))
                self.assertEqual(response.status_code, 200 if visible else 404)

            if viewer != "anonymous":
                with self.subTest(viewer=viewer, status=status, visibility=visibility, place="archive"):
                    response = self.client.get(reverse("download_version_archive", kwargs={
                        "work_id": work.id, "version_id": version.id,
                    }))
                    self.assertEqual(response.status_code, 200 if visible else 404)

                with self.subTest(viewer=viewer, status=status, visibility=visibility, place="all_works"):
                    response = self.client.get(reverse("all_works"))
                    self.assertEqual(work in response.context["works"], visible)

            with self.subTest(viewer=viewer, status=status, visibility=visibility, place="section"):
                response = self.client.get(reverse("section_detail", kwargs={"section_id": self.section.id}))
                self.assertEqual(work in response.context["works"], visible)

            with self.subTest(viewer=viewer, status=status, visibility=visibility, place="search"):
                response = self.client.get(reverse("home"), {"q": f"секрет-{status}-{visibility}"})
                self.assertEqual(work in response.context["search_results"], visible)

    def test_section_counts_follow_visibility(self):
        expected = {"anonymous": 1, "other": 1, "author": 4, "admin": 4}
        for viewer, count in expected.items():
            self.login(viewer)
            with self.subTest(viewer=viewer):
                response = self.client.get(reverse("home"))
                section = next(item for item in response.context["sections"] if item.id == self.section.id)
                self.assertEqual(section.work_count, count)

    def test_only_author_and_admin_can_edit(self):
        work, _, _ = self.works[("published", "public")]
        for viewer, expected in (("other", 403), ("author", 200), ("admin", 200)):
            self.login(viewer)
            with self.subTest(viewer=viewer):
                response = self.client.get(reverse("update_work", kwargs={"work_id": work.id}))
                self.assertEqual(response.status_code, expected)
