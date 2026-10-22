import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings


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
