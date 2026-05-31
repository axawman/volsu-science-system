from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_group_chat_replies_reads_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="last_seen_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Был онлайн"),
        ),
        migrations.AddField(
            model_name="groupchatmessage",
            name="hidden_for",
            field=models.ManyToManyField(
                blank=True,
                related_name="hidden_group_chat_messages",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Скрыто для пользователей",
            ),
        ),
    ]
