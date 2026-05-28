from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    verbose_name = "Профиль"
    verbose_name_plural = "Профиль"


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "get_profile_role")

    @admin.display(description="Роль", ordering="profile__role")
    def get_profile_role(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.get_role_display()
        return "-"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("user__username", "user__email", "full_name", "bio")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    list_select_related = ("user",)
