"""
In-browser IDE domain.

A Project holds a set of text ProjectFiles (each named ``name.ext``). From the
IDE a developer can Run (terminal: ``python main.py``) and Deploy — deploying
writes the files into a playable Game bundle. Story projects deploy each
``scene_<n>.html`` as an auto-advancing GameScene.
"""

from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from .languages import language_for


class Project(models.Model):
    class Kind(models.TextChoices):
        NORMAL = "normal", "Normal game (HTML)"
        STORY = "story", "Story game (scenes)"
        CODE = "code", "Code program"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.NORMAL)
    # The Game produced by the most recent Deploy (if any).
    deployed_game = models.ForeignKey(
        "games.Game", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} (@{self.owner.username})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "project"
            self.slug = f"{base}-{get_random_string(6).lower()}"
        super().save(*args, **kwargs)


class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="files")
    path = models.CharField(max_length=255, help_text="e.g. main.py, index.html")
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "path"]
        constraints = [
            models.UniqueConstraint(fields=["project", "path"], name="uniq_project_file"),
        ]

    def __str__(self):
        return f"{self.project.slug}/{self.path}"

    @property
    def language(self):
        return language_for(self.path)
