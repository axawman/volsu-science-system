from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_chat_hidden_messages_and_presence"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="groupchatmessage",
            new_name="accounts_gr_study_g_58b431_idx",
            old_name="accounts_gr_study__8b9065_idx",
        ),
    ]
