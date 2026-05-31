from django.contrib import admin
from django.apps import apps
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User

from .models import Profile


apps.get_app_config("auth").verbose_name = "Пользователи"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fields = ("full_name", "role", "bio", "photo", "created_at")
    readonly_fields = ("created_at",)
    verbose_name = "Профиль"
    verbose_name_plural = "Профиль"


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "get_full_name",
        "get_profile_role",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "profile__role", "date_joined")
    list_select_related = ("profile",)
    search_fields = ("username", "email", "profile__full_name", "profile__bio")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Контакты", {"fields": ("email",)}),
        ("Права доступа", {
            "fields": ("is_active", "is_staff", "is_superuser", "user_permissions"),
        }),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )

    @admin.display(description="ФИО", ordering="profile__full_name")
    def get_full_name(self, obj):
        if hasattr(obj, "profile") and obj.profile.full_name:
            return obj.profile.full_name
        return obj.get_full_name() or "-"

    @admin.display(description="Роль", ordering="profile__role")
    def get_profile_role(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.get_role_display()
        return "-"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.unregister(Group)
