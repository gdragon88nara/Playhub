from django.contrib import admin

from .models import Post, PostComment, PostLike, PostMedia


class MediaInline(admin.TabularInline):
    model = PostMedia
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "visibility", "created_at")
    list_filter = ("visibility",)
    search_fields = ("author__username", "body")
    inlines = [MediaInline]


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")


admin.site.register(PostLike)
