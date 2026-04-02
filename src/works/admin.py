from django.contrib import admin
from .models import Work, WorkVersion


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "visibility", "created_at")
    list_filter = ("status", "visibility")
    search_fields = ("title", "description", "author__username")


@admin.register(WorkVersion)
class WorkVersionAdmin(admin.ModelAdmin):
    list_display = ("work", "version_number", "uploaded_by", "created_at")
    search_fields = ("work__title", "uploaded_by__username")