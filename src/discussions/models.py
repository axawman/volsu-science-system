from django.db import models
from django.contrib.auth.models import User
from works.models import Work


class WorkComment(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="work_comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.work.title}"