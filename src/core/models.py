from django.db import models


class PlatformNews(models.Model):
    title = models.CharField("Заголовок", max_length=255)
    text = models.TextField("Текст", blank=True)
    image = models.ImageField("Фотография", upload_to="platform_news/", blank=True, null=True)
    is_active = models.BooleanField("Показывать", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = "Новость платформы"
        verbose_name_plural = "Новости платформы"

    def __str__(self):
        return self.title
