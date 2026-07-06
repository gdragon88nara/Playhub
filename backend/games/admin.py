from django.contrib import admin

from .models import Comment, Game, GameScene, Like, SavedGame


class SceneInline(admin.TabularInline):
    model = GameScene
    extra = 0


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "engine", "kind", "visibility", "status",
                    "is_paid", "price", "play_count", "created_at")
    list_filter = ("engine", "kind", "visibility", "status", "is_paid")
    search_fields = ("title", "owner__username", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [SceneInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("game", "user", "created_at")
    search_fields = ("game__title", "user__username")


admin.site.register(Like)
admin.site.register(SavedGame)
