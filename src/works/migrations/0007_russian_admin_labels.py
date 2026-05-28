from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("works", "0006_alter_work_status_alter_work_visibility"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="work",
            options={"ordering": ["-created_at"], "verbose_name": "Научная работа", "verbose_name_plural": "Научные работы"},
        ),
        migrations.AlterModelOptions(
            name="workversion",
            options={
                "ordering": ["-version_number"],
                "verbose_name": "Версия работы",
                "verbose_name_plural": "Версии работ",
            },
        ),
        migrations.AlterModelOptions(
            name="workversionfile",
            options={"ordering": ["id"], "verbose_name": "Файл версии", "verbose_name_plural": "Файлы версий"},
        ),
        migrations.AlterField(
            model_name="work",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="works",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Автор",
            ),
        ),
        migrations.AlterField(
            model_name="work",
            name="content",
            field=models.TextField(blank=True, verbose_name="Содержимое"),
        ),
        migrations.AlterField(
            model_name="work",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Создано"),
        ),
        migrations.AlterField(
            model_name="work",
            name="description",
            field=models.TextField(blank=True, verbose_name="Краткое описание"),
        ),
        migrations.AlterField(
            model_name="work",
            name="status",
            field=models.CharField(
                choices=[("draft", "Черновик"), ("published", "Опубликовано")],
                default="draft",
                max_length=20,
                verbose_name="Статус",
            ),
        ),
        migrations.AlterField(
            model_name="work",
            name="title",
            field=models.CharField(max_length=255, verbose_name="Название"),
        ),
        migrations.AlterField(
            model_name="work",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
        ),
        migrations.AlterField(
            model_name="work",
            name="visibility",
            field=models.CharField(
                choices=[("private", "Скрытая"), ("public", "Открытая")],
                default="private",
                max_length=20,
                verbose_name="Видимость",
            ),
        ),
        migrations.AlterField(
            model_name="worksection",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AlterField(
            model_name="worksection",
            name="name",
            field=models.CharField(max_length=150, unique=True, verbose_name="Название"),
        ),
        migrations.AlterField(
            model_name="worksection",
            name="sort_order",
            field=models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки"),
        ),
        migrations.AlterField(
            model_name="workversion",
            name="comment",
            field=models.TextField(blank=True, verbose_name="Комментарий"),
        ),
        migrations.AlterField(
            model_name="workversion",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки"),
        ),
        migrations.AlterField(
            model_name="workversion",
            name="file",
            field=models.FileField(blank=True, null=True, upload_to="work_versions/", verbose_name="Файл"),
        ),
        migrations.AlterField(
            model_name="workversion",
            name="uploaded_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="uploaded_work_versions",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Загрузил",
            ),
        ),
        migrations.AlterField(
            model_name="workversion",
            name="version_number",
            field=models.PositiveIntegerField(verbose_name="Номер версии"),
        ),
        migrations.AlterField(
            model_name="workversion",
            name="work",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="versions",
                to="works.work",
                verbose_name="Работа",
            ),
        ),
        migrations.AlterField(
            model_name="workversionfile",
            name="file",
            field=models.FileField(upload_to="work_versions/", verbose_name="Файл"),
        ),
        migrations.AlterField(
            model_name="workversionfile",
            name="original_name",
            field=models.CharField(blank=True, max_length=255, verbose_name="Исходное имя файла"),
        ),
        migrations.AlterField(
            model_name="workversionfile",
            name="uploaded_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки"),
        ),
        migrations.AlterField(
            model_name="workversionfile",
            name="version",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="files",
                to="works.workversion",
                verbose_name="Версия",
            ),
        ),
    ]
