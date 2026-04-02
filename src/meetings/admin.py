from django.contrib import admin
from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "start_at", "end_at", "created_by")
    list_filter = ("start_at",)
    search_fields = ("title", "description")