from django.db import migrations, models
import django.db.models.deletion


def copy_existing_files(apps, schema_editor):
    WorkVersion = apps.get_model("works", "WorkVersion")
    WorkVersionFile = apps.get_model("works", "WorkVersionFile")

    for version in WorkVersion.objects.exclude(file=""):
        if version.file:
            WorkVersionFile.objects.create(
                version=version,
                file=version.file.name,
                original_name=version.file.name.rsplit("/", 1)[-1],
            )


class Migration(migrations.Migration):

    dependencies = [
        ("works", "0003_work_content"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workversion",
            name="file",
            field=models.FileField(blank=True, null=True, upload_to="work_versions/"),
        ),
        migrations.CreateModel(
            name="WorkVersionFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="work_versions/")),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("version", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="files", to="works.workversion")),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.RunPython(copy_existing_files, migrations.RunPython.noop),
    ]
