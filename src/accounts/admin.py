from django.contrib import admin
from django.apps import apps
from django.contrib import messages
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
    actions = ("make_admin",)
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
            return obj.profile.role_name
        return "-"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user = form.instance

        if hasattr(user, "profile") and user.profile.role == "admin":
            update_fields = []

            if not user.is_staff:
                user.is_staff = True
                update_fields.append("is_staff")

            if not user.is_superuser:
                user.is_superuser = True
                update_fields.append("is_superuser")

            if update_fields:
                user.save(update_fields=update_fields)

    @admin.action(description="Назначить администратором")
    def make_admin(self, request, queryset):
        updated = 0

        for user in queryset.select_related("profile"):
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={"full_name": user.username},
            )
            changed = False
            user_update_fields = []

            if profile.role != "admin":
                profile.role = "admin"
                profile.save(update_fields=["role"])
                changed = True

            if not user.is_staff:
                user.is_staff = True
                user_update_fields.append("is_staff")
                changed = True

            if not user.is_superuser:
                user.is_superuser = True
                user_update_fields.append("is_superuser")
                changed = True

            if user_update_fields:
                user.save(update_fields=user_update_fields)

            if changed:
                updated += 1

        self.message_user(
            request,
            f"Администратором назначено пользователей: {updated}.",
            messages.SUCCESS,
        )


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.unregister(Group)
