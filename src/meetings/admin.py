from django.contrib import admin
from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "start_at", "end_at", "location", "created_by")
    list_filter = ("start_at", "end_at")
    search_fields = ("title", "description", "location", "created_by__username", "created_by__email")
    readonly_fields = ("updated_at",)
    autocomplete_fields = ("created_by",)
    date_hierarchy = "start_at"
    list_select_related = ("created_by",)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
