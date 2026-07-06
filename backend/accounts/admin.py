from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Follow, FollowRequest, SellerProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("id",)
    list_display = ("id", "username", "email", "is_private", "is_seller", "is_staff")
    list_filter = ("is_private", "is_seller", "is_staff", "is_superuser")
    search_fields = ("username", "email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Profile", {"fields": ("display_name", "bio", "avatar", "is_private")}),
        ("Roles", {"fields": ("is_seller", "is_active", "is_staff", "is_superuser",
                              "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2"),
        }),
    )


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "onboarding_status", "payouts_enabled",
                    "provider", "commission_rate")
    list_filter = ("onboarding_status", "payouts_enabled", "provider")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")


@admin.register(FollowRequest)
class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ("requester", "target", "status", "created_at", "resolved_at")
    list_filter = ("status",)
