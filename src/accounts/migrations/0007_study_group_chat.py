import re

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


PROGRAM_LABELS = {
    "pmi": "ПМИ",
}
LEVEL_LABELS = {
    "b": "б",
    "m": "м",
    "s": "с",
}


def parse_group(email):
    if not email:
        return None

    try:
        local_part, domain = email.strip().lower().split("@", 1)
        group_code, record_book_number = local_part.rsplit("_", 1)
    except ValueError:
        return None

    if domain != "volsu.ru" or not record_book_number.isdigit():
        return None

    match = re.fullmatch(r"([a-z]+)-(\d+)", group_code)
    if not match:
        return None

    letter_code = match.group(1)
    group_number = match.group(2)
    if len(letter_code) < 2:
        return None

    program_code = letter_code[:-1]
    level_code = letter_code[-1]
    program_label = PROGRAM_LABELS.get(program_code, program_code.upper())
    level_label = LEVEL_LABELS.get(level_code, level_code)

    return group_code, f"{program_label}{level_label}-{group_number}"


def assign_existing_student_groups(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    StudyGroup = apps.get_model("accounts", "StudyGroup")

    profiles = Profile.objects.select_related("user").filter(role="student")
    for profile in profiles:
        group_data = parse_group(profile.user.email)
        if not group_data:
            continue

        group_code, group_name = group_data
        study_group, _ = StudyGroup.objects.get_or_create(
            code=group_code,
            defaults={"display_name": group_name},
        )
        profile.study_group = study_group
        profile.save(update_fields=["study_group"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0006_admin_grant_ownership"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudyGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True, verbose_name="Код группы")),
                ("display_name", models.CharField(max_length=64, verbose_name="Название группы")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
            ],
            options={
                "verbose_name": "Учебная группа",
                "verbose_name_plural": "Учебные группы",
                "ordering": ("display_name",),
            },
        ),
        migrations.AddField(
            model_name="profile",
            name="study_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="accounts.studygroup",
                verbose_name="Учебная группа",
            ),
        ),
        migrations.CreateModel(
            name="GroupChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(verbose_name="Текст сообщения")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_chat_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Автор",
                    ),
                ),
                (
                    "study_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="accounts.studygroup",
                        verbose_name="Учебная группа",
                    ),
                ),
            ],
            options={
                "verbose_name": "Сообщение группового чата",
                "verbose_name_plural": "Сообщения группового чата",
                "ordering": ("created_at", "id"),
            },
        ),
        migrations.RunPython(assign_existing_student_groups, noop_reverse),
    ]
