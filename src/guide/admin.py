from django.contrib import admin

from .models import GuideFile, GuideSection


class GuideFileInline(admin.TabularInline):
    model = GuideFile
    extra = 0
    fields = ("title", "description", "file", "is_published", "sort_order")


@admin.register(GuideSection)
class GuideSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "sort_order", "updated_at")
    list_editable = ("is_published", "sort_order")
    list_filter = ("is_published",)
    search_fields = ("title", "summary", "content")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    fields = ("title", "slug", "summary", "content", "is_published", "sort_order", "created_at", "updated_at")
    inlines = (GuideFileInline,)


@admin.register(GuideFile)
class GuideFileAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "is_published", "sort_order", "created_at")
    list_editable = ("is_published", "sort_order")
    list_filter = ("is_published", "section")
    search_fields = ("title", "description")
    readonly_fields = ("created_at",)
    fields = ("title", "description", "file", "section", "is_published", "sort_order", "created_at")
