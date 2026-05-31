from django.contrib import admin

from .models import PlatformNews

admin.site.site_header = "Администрирование ScienceHub ВолГУ"
admin.site.site_title = "ScienceHub ВолГУ"
admin.site.index_title = "Управление данными ScienceHub"


@admin.register(PlatformNews)
class PlatformNewsAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "sort_order", "created_at", "updated_at")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "text")
    readonly_fields = ("created_at", "updated_at")
    fields = ("title", "text", "image", "is_active", "sort_order", "created_at", "updated_at")
