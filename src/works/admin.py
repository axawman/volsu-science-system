from django.contrib import admin
from .models import Work, WorkSection, WorkVersion, WorkVersionFile


class WorkVersionFileInline(admin.TabularInline):
    model = WorkVersionFile
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(WorkSection)
class WorkSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    search_fields = ("name", "description")
    ordering = ("sort_order", "name")


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "section", "status", "visibility", "created_at")
    list_filter = ("section", "status", "visibility", "created_at")
    search_fields = ("title", "description", "content", "author__username", "author__email", "section__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("author", "section")
    date_hierarchy = "created_at"
    list_select_related = ("author", "section")
    ordering = ("-created_at",)


@admin.register(WorkVersion)
class WorkVersionAdmin(admin.ModelAdmin):
    list_display = ("work", "version_number", "get_file_count", "uploaded_by", "created_at")
    search_fields = ("work__title", "comment", "uploaded_by__username", "uploaded_by__email")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("work", "uploaded_by")
    list_select_related = ("work", "uploaded_by")
    inlines = (WorkVersionFileInline,)

    @admin.display(description="Файлов")
    def get_file_count(self, obj):
        return obj.file_count


@admin.register(WorkVersionFile)
class WorkVersionFileAdmin(admin.ModelAdmin):
    list_display = ("get_filename", "version", "uploaded_at")
    search_fields = ("original_name", "file", "version__work__title")
    readonly_fields = ("uploaded_at",)
    autocomplete_fields = ("version",)
    list_select_related = ("version", "version__work")

    @admin.display(description="Файл")
    def get_filename(self, obj):
        return obj.filename
