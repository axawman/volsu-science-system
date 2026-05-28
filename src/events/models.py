from django.db import models
from django.contrib.auth.models import User


class Event(models.Model):
    title = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)
    event_date = models.DateTimeField("Дата и время")
    location = models.CharField("Место проведения", max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_events", verbose_name="Добавил")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        ordering = ["event_date"]
        verbose_name = "Событие"
        verbose_name_plural = "События"

    def __str__(self):
        return self.title
