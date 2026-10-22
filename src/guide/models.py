import os

from django.db import models
from django.urls import reverse


class GuideSection(models.Model):
    title = models.CharField("Заголовок", max_length=255)
    slug = models.SlugField(
        "Адрес страницы",
        max_length=100,
        unique=True,
        help_text="Латиница, цифры и дефисы, например: oformlenie-teksta",
    )
    summary = models.CharField(
        "Краткое описание",
        max_length=300,
        blank=True,
        help_text="Показывается в списке разделов на главной и в оглавлении справочника",
    )
    content = models.TextField(
        "Текст",
        blank=True,
        help_text="Поддерживается Markdown: заголовки ##, списки, таблицы, **полужирный**, > цитаты",
    )
    is_published = models.BooleanField("Опубликовано", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "Раздел справочника"
        verbose_name_plural = "Разделы справочника"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("guide_section", kwargs={"slug": self.slug})


class GuideFile(models.Model):
    section = models.ForeignKey(
        GuideSection,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Раздел",
        blank=True,
        null=True,
        help_text="Оставьте пустым, чтобы файл был общим: он появится на главной и в оглавлении справочника",
    )
    title = models.CharField("Название", max_length=255)
    description = models.CharField("Описание", max_length=300, blank=True)
    file = models.FileField("Файл", upload_to="guide/")
    is_published = models.BooleanField("Опубликовано", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "Файл справочника"
        verbose_name_plural = "Файлы справочника"

    def __str__(self):
        return self.title

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def extension(self):
        return os.path.splitext(self.file.name)[1].lstrip(".").upper()

    def get_absolute_url(self):
        return reverse("guide_file_download", kwargs={"file_id": self.id})
