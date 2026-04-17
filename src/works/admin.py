from django.contrib import admin
from .models import Work, WorkSection, WorkVersion


@admin.register(WorkSection)
class WorkSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    search_fields = ("name", "description")
    ordering = ("sort_order", "name")


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "section", "status", "visibility", "created_at")
    list_filter = ("section", "status", "visibility")
    search_fields = ("title", "description", "author__username", "section__name")


@admin.register(WorkVersion)
class WorkVersionAdmin(admin.ModelAdmin):
    list_display = ("work", "version_number", "uploaded_by", "created_at")
    search_fields = ("work__title", "uploaded_by__username")
