import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from .models import GuideFile, GuideSection


class GuideInitialContentTests(TestCase):
    def test_migration_creates_published_sections(self):
        sections = GuideSection.objects.filter(is_published=True)

        self.assertTrue(sections.filter(slug="oformlenie-teksta").exists())
        self.assertFalse(sections.filter(content="").exists())


class GuideViewsTests(TestCase):
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
        GuideSection.objects.all().delete()
        self.published = GuideSection.objects.create(
            title="Оформление текста", slug="text", content="## Поля", sort_order=1
        )
        self.hidden = GuideSection.objects.create(
            title="Черновик", slug="draft", is_published=False, sort_order=2
        )

    def create_file(self, **kwargs):
        return GuideFile.objects.create(
            title="Шаблон",
            file=SimpleUploadedFile("template.docx", b"docx-content"),
            **kwargs,
        )

    def test_index_lists_only_published_sections(self):
        response = self.client.get(reverse("guide_index"))

        self.assertContains(response, "Оформление текста")
        self.assertNotContains(response, "Черновик")

    def test_hidden_section_returns_404_for_regular_user(self):
        response = self.client.get(reverse("guide_section", kwargs={"slug": "draft"}))

        self.assertEqual(response.status_code, 404)

    def test_staff_can_preview_hidden_section(self):
        staff = User.objects.create_user("staff", password="password", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("guide_section", kwargs={"slug": "draft"}))

        self.assertContains(response, "Скрыт от пользователей")

    def test_section_page_links_to_neighbours(self):
        GuideSection.objects.create(title="Таблицы", slug="tables", sort_order=3)

        response = self.client.get(reverse("guide_section", kwargs={"slug": "text"}))

        self.assertIsNone(response.context["previous_section"])
        self.assertEqual(response.context["next_section"].slug, "tables")

    def test_published_file_downloads(self):
        guide_file = self.create_file()

        response = self.client.get(reverse("guide_file_download", kwargs={"file_id": guide_file.id}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"docx-content")

    def test_file_of_hidden_section_is_not_downloadable(self):
        guide_file = self.create_file(section=self.hidden)

        response = self.client.get(reverse("guide_file_download", kwargs={"file_id": guide_file.id}))

        self.assertEqual(response.status_code, 404)

    def test_unpublished_file_is_not_downloadable(self):
        guide_file = self.create_file(is_published=False)

        response = self.client.get(reverse("guide_file_download", kwargs={"file_id": guide_file.id}))

        self.assertEqual(response.status_code, 404)

    def test_home_shows_guide_sections_and_general_files(self):
        self.create_file()
        GuideFile.objects.create(
            title="Файл раздела",
            section=self.published,
            file=SimpleUploadedFile("section.pdf", b"pdf-content"),
        )

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Оформление текста")
        self.assertContains(response, "Шаблон")
        self.assertNotContains(response, "Файл раздела")
        self.assertNotContains(response, "Черновик")
