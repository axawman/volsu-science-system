from django.db import models
from django.contrib.auth.models import User


class Work(models.Model):
    STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("published", "Опубликовано"),
    ]

    VISIBILITY_CHOICES = [
        ("private", "Открытая"),
        ("public", "Скрытая"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="works")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="private")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class WorkVersion(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="work_versions/")
    comment = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploaded_work_versions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ("work", "version_number")

    def __str__(self):
        return f"{self.work.title} v{self.version_number}"
