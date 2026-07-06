from django.contrib import admin

from .models import Short, ShortLike


@admin.register(Short)
class ShortAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "visibility", "view_count", "created_at")
    list_filter = ("visibility",)
    search_fields = ("author__username", "caption")


admin.site.register(ShortLike)
