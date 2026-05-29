from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("discussions", "0002_russian_admin_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="workcomment",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="replies",
                to="discussions.workcomment",
                verbose_name="Ответ на комментарий",
            ),
        ),
    ]
