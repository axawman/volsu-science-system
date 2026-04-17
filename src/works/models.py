from django.db import models
from django.contrib.auth.models import User


class WorkSection(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Раздел работ"
        verbose_name_plural = "Разделы работ"

    def __str__(self):
        return self.name


class Work(models.Model):
    STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("published", "Опубликовано"),
    ]

    VISIBILITY_CHOICES = [
        ("private", "Скрытая"),
        ("public", "Открытая"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="works")
    section = models.ForeignKey(
        WorkSection,
        on_delete=models.SET_NULL,
        related_name="works",
        null=True,
        blank=True,
        verbose_name="Раздел",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="private")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class WorkVersion(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="work_versions/", blank=True, null=True)
    comment = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploaded_work_versions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ("work", "version_number")

    def __str__(self):
        return f"{self.work.title} v{self.version_number}"

    @property
    def file_count(self):
        return self.files.count()


class WorkVersionFile(models.Model):
    version = models.ForeignKey(WorkVersion, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="work_versions/")
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.original_name or self.filename

    @property
    def filename(self):
        return self.original_name or self.file.name.rsplit("/", 1)[-1]
