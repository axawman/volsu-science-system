import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_admin_grant_ownership(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    User = apps.get_model("auth", "User")

    admin_users = User.objects.filter(is_staff=True, is_superuser=True).order_by("date_joined", "id")
    primary_user = None

    primary_username = getattr(settings, "DJANGO_SUPERUSER_USERNAME", None)
    if primary_username:
        primary_user = admin_users.filter(username=primary_username).first()

    if primary_user is None:
        primary_user = admin_users.first()

    if primary_user is None:
        return

    for user in admin_users:
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={"full_name": user.username},
        )

        update_fields = []

        if profile.role != "admin":
            profile.role = "admin"
            update_fields.append("role")

        if user.id == primary_user.id:
            if not profile.is_primary_admin:
                profile.is_primary_admin = True
                update_fields.append("is_primary_admin")

            if profile.admin_granted_by_id is not None:
                profile.admin_granted_by = None
                update_fields.append("admin_granted_by")
        elif profile.admin_granted_by_id is None:
            profile.admin_granted_by = primary_user
            update_fields.append("admin_granted_by")

        if update_fields:
            profile.save(update_fields=update_fields)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0005_grant_superuser_to_profile_admins"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="admin_granted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="granted_admin_profiles",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Кто назначил администратором",
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="is_primary_admin",
            field=models.BooleanField(default=False, verbose_name="Первичный администратор"),
        ),
        migrations.RunPython(seed_admin_grant_ownership, noop_reverse),
    ]
