from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_study_group_chat"),
    ]

    operations = [
        migrations.AddField(
            model_name="groupchatmessage",
            name="edited_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Дата редактирования"),
        ),
    ]
