from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("meetings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="meeting",
            options={"ordering": ["start_at"], "verbose_name": "Встреча", "verbose_name_plural": "Встречи"},
        ),
        migrations.AlterField(
            model_name="meeting",
            name="created_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="created_meetings",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Создал",
            ),
        ),
        migrations.AlterField(
            model_name="meeting",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AlterField(
            model_name="meeting",
            name="end_at",
            field=models.DateTimeField(verbose_name="Окончание"),
        ),
        migrations.AlterField(
            model_name="meeting",
            name="location",
            field=models.CharField(blank=True, max_length=255, verbose_name="Место проведения"),
        ),
        migrations.AlterField(
            model_name="meeting",
            name="start_at",
            field=models.DateTimeField(verbose_name="Начало"),
        ),
        migrations.AlterField(
            model_name="meeting",
            name="title",
            field=models.CharField(max_length=255, verbose_name="Название"),
        ),
        migrations.AlterField(
            model_name="meeting",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
        ),
    ]
