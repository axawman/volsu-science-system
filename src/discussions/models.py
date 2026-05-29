from django.db import models
from django.contrib.auth.models import User
from works.models import Work


class WorkComment(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="comments", verbose_name="Работа")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
        verbose_name="Ответ на комментарий",
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="work_comments", verbose_name="Автор")
    text = models.TextField("Текст комментария")
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"Комментарий {self.author.username} к работе {self.work.title}"
