from django.contrib import admin
from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    fields = ("title", "description", "start_at", "location", "get_created_by", "updated_at")
    list_display = ("title", "start_at", "location", "created_by")
    list_filter = ("start_at",)
    search_fields = ("title", "description", "location", "created_by__username", "created_by__email")
    readonly_fields = ("get_created_by", "updated_at")
    date_hierarchy = "start_at"
    list_select_related = ("created_by",)

    @admin.display(description="Создал")
    def get_created_by(self, obj):
        return obj.created_by if obj and obj.created_by_id else "Будет указан автоматически"

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
