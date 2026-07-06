"""
Short-form vertical videos (Reels/TikTok-style).

Video files live in the protected root and are served only via a signed-URL
view — the same in-site-only guarantee used for games and post media.
"""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class ProtectedShortStorage(FileSystemStorage):
    @property
    def base_location(self):
        return str(settings.SHORTS_ROOT)

    @property
    def location(self):
        return os.path.abspath(str(settings.SHORTS_ROOT))


protected_short_storage = ProtectedShortStorage()


def short_video_path(instance, filename):
    return f"{instance.author_id}/{filename}"


class Short(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS = "followers", "Followers only"
        PRIVATE = "private", "Private (only me)"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shorts"
    )
    caption = models.CharField(max_length=300, blank=True)
    video = models.FileField(upload_to=short_video_path, storage=protected_short_storage)
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["visibility", "-created_at"])]

    def __str__(self):
        return f"Short #{self.pk} by @{self.author.username}"

    @property
    def likes_count(self):
        return self.likes.count()

    def visible_to(self, viewer) -> bool:
        is_author = bool(viewer and viewer.is_authenticated and viewer.pk == self.author_id)
        if is_author:
            return True
        if self.visibility == self.Visibility.PRIVATE:
            return False
        if self.visibility == self.Visibility.FOLLOWERS or self.author.is_private:
            if viewer is None or not viewer.is_authenticated:
                return False
            from accounts.models import Follow
            return Follow.objects.filter(follower=viewer, following=self.author).exists()
        return True


class ShortLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    short = models.ForeignKey(Short, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "short"], name="uniq_short_like")
        ]
