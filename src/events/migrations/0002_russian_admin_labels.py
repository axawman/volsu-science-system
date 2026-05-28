from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="event",
            options={"ordering": ["event_date"], "verbose_name": "Событие", "verbose_name_plural": "События"},
        ),
        migrations.AlterField(
            model_name="event",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Дата создания"),
        ),
        migrations.AlterField(
            model_name="event",
            name="created_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="created_events",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Добавил",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AlterField(
            model_name="event",
            name="event_date",
            field=models.DateTimeField(verbose_name="Дата и время"),
        ),
        migrations.AlterField(
            model_name="event",
            name="location",
            field=models.CharField(blank=True, max_length=255, verbose_name="Место проведения"),
        ),
        migrations.AlterField(
            model_name="event",
            name="title",
            field=models.CharField(max_length=255, verbose_name="Название"),
        ),
    ]
