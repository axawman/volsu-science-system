from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("discussions", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="workcomment",
            options={"ordering": ["-created_at"], "verbose_name": "Комментарий", "verbose_name_plural": "Комментарии"},
        ),
        migrations.AlterField(
            model_name="workcomment",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="work_comments",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Автор",
            ),
        ),
        migrations.AlterField(
            model_name="workcomment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Создано"),
        ),
        migrations.AlterField(
            model_name="workcomment",
            name="text",
            field=models.TextField(verbose_name="Текст комментария"),
        ),
        migrations.AlterField(
            model_name="workcomment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
        ),
        migrations.AlterField(
            model_name="workcomment",
            name="work",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to="works.work",
                verbose_name="Работа",
            ),
        ),
    ]
