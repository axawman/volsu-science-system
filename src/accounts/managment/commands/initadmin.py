from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings


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
            self.stdout.write(self.style.SUCCESS(f"Суперпользователь '{username}' уже существует"))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Суперпользователь '{username}' создан"))