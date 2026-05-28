from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_profile_role"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="profile",
            options={"verbose_name": "Профиль", "verbose_name_plural": "Профили"},
        ),
        migrations.AlterField(
            model_name="profile",
            name="bio",
            field=models.TextField(blank=True, verbose_name="О себе"),
        ),
        migrations.AlterField(
            model_name="profile",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Дата создания"),
        ),
        migrations.AlterField(
            model_name="profile",
            name="full_name",
            field=models.CharField(max_length=255, verbose_name="ФИО"),
        ),
        migrations.AlterField(
            model_name="profile",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="profile_photos/", verbose_name="Фотография"),
        ),
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[("student", "Студент"), ("teacher", "Преподаватель"), ("admin", "Администратор")],
                default="student",
                max_length=20,
                verbose_name="Роль",
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="profile",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Пользователь",
            ),
        ),
    ]
