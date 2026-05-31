import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0008_group_chat_message_edited_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="groupchatmessage",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Дата удаления"),
        ),
        migrations.AddField(
            model_name="groupchatmessage",
            name="is_deleted",
            field=models.BooleanField(default=False, verbose_name="Удалено"),
        ),
        migrations.AddField(
            model_name="groupchatmessage",
            name="read_by",
            field=models.ManyToManyField(
                blank=True,
                related_name="read_group_chat_messages",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Кем прочитано",
            ),
        ),
        migrations.AddField(
            model_name="groupchatmessage",
            name="reply_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replies",
                to="accounts.groupchatmessage",
                verbose_name="Ответ на сообщение",
            ),
        ),
        migrations.AddIndex(
            model_name="groupchatmessage",
            index=models.Index(
                fields=["study_group", "created_at", "id"],
                name="accounts_gr_study__8b9065_idx",
            ),
        ),
    ]
