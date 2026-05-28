from django.db import models
from django.contrib.auth.models import User


class Meeting(models.Model):
    title = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)
    start_at = models.DateTimeField("Начало")
    end_at = models.DateTimeField("Окончание")
    location = models.CharField("Место проведения", max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_meetings", verbose_name="Создал")
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["start_at"]
        verbose_name = "Встреча"
        verbose_name_plural = "Встречи"

    def __str__(self):
        return self.title
