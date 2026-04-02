from django.contrib import admin
from .models import WorkComment


@admin.register(WorkComment)
class WorkCommentAdmin(admin.ModelAdmin):
    list_display = ("work", "author", "created_at")
    search_fields = ("text", "author__username", "work__title")