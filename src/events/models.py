from datetime import timedelta

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


class PersonalEvent(models.Model):
    REMIND_CHOICES = [
        (0, "В момент начала"),
        (15, "За 15 минут"),
        (60, "За 1 час"),
        (180, "За 3 часа"),
        (1440, "За 1 день"),
        (4320, "За 3 дня"),
        (10080, "За неделю"),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="personal_events",
        verbose_name="Владелец",
    )
    title = models.CharField("Название", max_length=255)
    description = models.TextField("Заметка", blank=True)
    starts_at = models.DateTimeField("Дата и время")
    remind_before = models.PositiveIntegerField(
        "Напоминание",
        choices=REMIND_CHOICES,
        blank=True,
        null=True,
    )
    remind_at = models.DateTimeField("Время напоминания", blank=True, null=True, editable=False)
    reminder_dismissed_at = models.DateTimeField("Напоминание скрыто", blank=True, null=True)
    reminder_emailed_at = models.DateTimeField("Напоминание отправлено на почту", blank=True, null=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "Личная запись"
        verbose_name_plural = "Личные записи"
        indexes = [
            models.Index(fields=["owner", "starts_at"]),
            models.Index(fields=["owner", "remind_at"]),
            models.Index(fields=["remind_at", "reminder_emailed_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.remind_before is None:
            self.remind_at = None
        else:
            self.remind_at = self.starts_at - timedelta(minutes=self.remind_before)

        update_fields = kwargs.get("update_fields")
        if update_fields is not None and {"starts_at", "remind_before"} & set(update_fields):
            kwargs["update_fields"] = {*update_fields, "remind_at"}

        super().save(*args, **kwargs)
