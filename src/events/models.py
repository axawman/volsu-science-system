from django.db import models
from django.contrib.auth.models import User


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_events")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title