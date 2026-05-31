from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("meetings", "0002_russian_admin_labels"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="meeting",
            name="end_at",
        ),
    ]
