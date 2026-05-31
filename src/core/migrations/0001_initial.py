from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PlatformNews",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Заголовок")),
                ("text", models.TextField(blank=True, verbose_name="Текст")),
                (
                    "image",
                    models.ImageField(blank=True, null=True, upload_to="platform_news/", verbose_name="Фотография"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Показывать")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
            ],
            options={
                "verbose_name": "Новость платформы",
                "verbose_name_plural": "Новости платформы",
                "ordering": ["sort_order", "-created_at"],
            },
        ),
    ]
