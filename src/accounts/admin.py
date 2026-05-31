from django.contrib import admin
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User

from .models import GroupChatMessage, Profile, StudyGroup
from .utils import get_student_record_book_number


apps.get_app_config("auth").verbose_name = "Пользователи"


def user_is_admin(user):
    if user.is_superuser or user.is_staff:
        return True
    return hasattr(user, "profile") and user.profile.role == "admin"


def can_manage_admin_target(actor, target):
    if actor == target:
        return False

    if not hasattr(target, "profile") or not user_is_admin(target):
        return True

    if target.profile.is_primary_admin:
        return False

    if hasattr(actor, "profile") and actor.profile.is_primary_admin:
        return True

    return target.profile.admin_granted_by_id == actor.id


def other_admins_exist(target):
    return (
        Profile.objects
        .exclude(user=target)
        .filter(role="admin", user__is_staff=True, user__is_superuser=True)
        .exists()
    )


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    can_delete = False
    extra = 0
    fields = (
        "full_name",
        "role",
        "bio",
        "photo",
        "study_group",
        "is_primary_admin",
        "admin_granted_by",
        "created_at",
    )
    readonly_fields = ("study_group", "is_primary_admin", "admin_granted_by", "created_at")
    verbose_name = "Профиль"
    verbose_name_plural = "Профиль"

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))

        if obj is not None and not can_manage_admin_target(request.user, obj):
            readonly_fields.append("role")

        return readonly_fields


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    actions = ("make_admin", "remove_admin")
    list_display = (
        "username",
        "email",
        "get_full_name",
        "get_profile_role",
        "get_record_book_number",
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

    @admin.display(description="Зачетная книжка")
    def get_record_book_number(self, obj):
        if hasattr(obj, "profile") and not obj.profile.is_student():
            return "-"

        return get_student_record_book_number(obj.email)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))

        if obj is not None and not can_manage_admin_target(request.user, obj):
            readonly_fields.extend(["is_staff", "is_superuser", "user_permissions"])

        return readonly_fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not can_manage_admin_target(request.user, obj):
            return False
        return super().has_delete_permission(request, obj)

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

            if not user.profile.is_primary_admin and user.profile.admin_granted_by_id is None:
                user.profile.admin_granted_by = request.user
                user.profile.save(update_fields=["admin_granted_by"])

    @admin.action(description="Назначить администратором")
    def make_admin(self, request, queryset):
        updated = 0

        for user in queryset.select_related("profile"):
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={"full_name": user.username},
            )
            changed = False
            profile_update_fields = []
            user_update_fields = []

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

            if profile.role != "admin":
                profile.role = "admin"
                profile_update_fields.append("role")
                changed = True

            if not profile.is_primary_admin and profile.admin_granted_by_id is None:
                profile.admin_granted_by = request.user
                profile_update_fields.append("admin_granted_by")
                changed = True

            if profile_update_fields:
                profile.save(update_fields=profile_update_fields)

            if changed:
                updated += 1

        self.message_user(
            request,
            f"Администратором назначено пользователей: {updated}.",
            messages.SUCCESS,
        )

    @admin.action(description="Убрать права администратора")
    def remove_admin(self, request, queryset):
        updated = 0
        skipped = 0

        for user in queryset.select_related("profile"):
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={"full_name": user.username},
            )

            if not profile.is_admin():
                skipped += 1
                continue

            if not can_manage_admin_target(request.user, user):
                skipped += 1
                continue

            if not other_admins_exist(user):
                skipped += 1
                continue

            user.is_staff = False
            user.is_superuser = False
            user.save(update_fields=["is_staff", "is_superuser"])

            profile.role = "student"
            profile.admin_granted_by = None
            profile.save(update_fields=["role", "admin_granted_by"])
            updated += 1

        if updated:
            self.message_user(
                request,
                f"Права администратора сняты у пользователей: {updated}.",
                messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                f"Не удалось снять права администратора у пользователей: {skipped}.",
                messages.WARNING,
            )


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.unregister(Group)


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ("display_name", "code", "get_member_count", "created_at")
    search_fields = ("display_name", "code")
    readonly_fields = ("created_at",)

    @admin.display(description="Студентов")
    def get_member_count(self, obj):
        return obj.members.count()


@admin.register(GroupChatMessage)
class GroupChatMessageAdmin(admin.ModelAdmin):
    list_display = ("study_group", "author", "created_at")
    list_filter = ("study_group", "created_at")
    search_fields = ("text", "author__username", "author__email", "author__profile__full_name")
    readonly_fields = ("created_at",)
    list_select_related = ("study_group", "author")
