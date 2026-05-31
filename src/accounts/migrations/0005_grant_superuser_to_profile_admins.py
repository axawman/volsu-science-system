from django.db import migrations


def grant_superuser_to_profile_admins(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    User = apps.get_model("auth", "User")

    admin_user_ids = Profile.objects.filter(role="admin").values_list("user_id", flat=True)
    User.objects.filter(id__in=admin_user_ids).update(is_staff=True, is_superuser=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_russian_admin_labels"),
    ]

    operations = [
        migrations.RunPython(grant_superuser_to_profile_admins, noop_reverse),
    ]
