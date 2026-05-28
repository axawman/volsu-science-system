from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="Пользователь")
    role = models.CharField("Роль", max_length=20, choices=ROLE_CHOICES, default="student")
    full_name = models.CharField("ФИО", max_length=255)
    bio = models.TextField("О себе", blank=True)
    photo = models.ImageField("Фотография", upload_to="profile_photos/", blank=True, null=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_admin(self):
        return self.role == "admin"

    def is_student(self):
        return self.role == "student"
