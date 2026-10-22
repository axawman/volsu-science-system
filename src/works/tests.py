from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Work


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
