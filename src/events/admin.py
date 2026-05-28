from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_date", "location", "created_by", "created_at")
    list_filter = ("event_date", "created_at")
    search_fields = ("title", "description", "location", "created_by__username", "created_by__email")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("created_by",)
    date_hierarchy = "event_date"
    list_select_related = ("created_by",)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
