from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("works", "0004_workversionfile_and_multi_upload"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["sort_order", "name"],
                "verbose_name": "Раздел работ",
                "verbose_name_plural": "Разделы работ",
            },
        ),
        migrations.AddField(
            model_name="work",
            name="section",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="works", to="works.worksection", verbose_name="Раздел"),
        ),
    ]
