from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

from accounts.models import Profile


class Command(BaseCommand):
    help = "Создает суперпользователя, если его еще нет"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = getattr(settings, "DJANGO_SUPERUSER_USERNAME", None)
        email = getattr(settings, "DJANGO_SUPERUSER_EMAIL", None)
        password = getattr(settings, "DJANGO_SUPERUSER_PASSWORD", None)

        if not username or not email or not password:
            self.stdout.write(self.style.WARNING("Переменные суперпользователя не заданы"))
            return

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={"full_name": user.username},
            )
            user_update_fields = []
            update_fields = []

            if not user.is_staff:
                user.is_staff = True
                user_update_fields.append("is_staff")

            if not user.is_superuser:
                user.is_superuser = True
                user_update_fields.append("is_superuser")

            if user_update_fields:
                user.save(update_fields=user_update_fields)

            if profile.role != "admin":
                profile.role = "admin"
                update_fields.append("role")

            if not profile.is_primary_admin:
                profile.is_primary_admin = True
                update_fields.append("is_primary_admin")

            if profile.admin_granted_by_id is not None:
                profile.admin_granted_by = None
                update_fields.append("admin_granted_by")

            if update_fields:
                profile.save(update_fields=update_fields)

            self.stdout.write(self.style.SUCCESS(f"Суперпользователь '{username}' уже существует"))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        user = User.objects.get(username=username)
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={"full_name": user.username},
        )
        profile.role = "admin"
        profile.is_primary_admin = True
        profile.admin_granted_by = None
        profile.save(update_fields=["role", "is_primary_admin", "admin_granted_by"])
        self.stdout.write(self.style.SUCCESS(f"Суперпользователь '{username}' создан"))
