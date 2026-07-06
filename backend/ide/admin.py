from django.contrib import admin

from .models import Project, ProjectFile


class FileInline(admin.TabularInline):
    model = ProjectFile
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "kind", "deployed_game", "updated_at")
    list_filter = ("kind",)
    search_fields = ("name", "owner__username")
    inlines = [FileInline]
