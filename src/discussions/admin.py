from django.contrib import admin
from .models import WorkComment


@admin.register(WorkComment)
class WorkCommentAdmin(admin.ModelAdmin):
    list_display = ("work", "author", "short_text", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("text", "author__username", "author__email", "work__title")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("work", "author")
    date_hierarchy = "created_at"
    list_select_related = ("work", "author")

    @admin.display(description="Комментарий")
    def short_text(self, obj):
        return obj.text[:80]
