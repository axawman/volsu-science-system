from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    full_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_admin(self):
        return self.role == "admin"

    def is_student(self):
        return self.role == "student"