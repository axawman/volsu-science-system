from django.db import models
from django.contrib.auth.models import User


class Meeting(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_meetings")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title