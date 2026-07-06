"""
Community domain — an Instagram-style feed.

A Post has text plus zero or more media (images/videos). Visibility mirrors the
games model and layers on account privacy. Post media is stored in the
protected root and served only through an authenticated, signed-URL view — so
private/followers content never leaks via a public URL.
"""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class ProtectedPostStorage(FileSystemStorage):
    """Filesystem storage whose location is read from ``POSTS_ROOT`` live (so it
    honours ``override_settings`` in tests and stays in the protected root).
    There is no public base_url — media is reachable only via the signed-URL
    serve view."""

    @property
    def base_location(self):
        return str(settings.POSTS_ROOT)

    @property
    def location(self):
        return os.path.abspath(str(settings.POSTS_ROOT))


protected_posts_storage = ProtectedPostStorage()


class Post(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS = "followers", "Followers only"
        PRIVATE = "private", "Private (only me)"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    body = models.TextField(blank=True, max_length=2200)
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["visibility", "-created_at"]),
        ]

    def __str__(self):
        return f"Post #{self.pk} by @{self.author.username}"

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

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


def post_media_path(instance, filename):
    return f"{instance.post_id}/{filename}"


class PostMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=8, choices=MediaType.choices)
    file = models.FileField(upload_to=post_media_path, storage=protected_posts_storage)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.media_type} for post #{self.post_id}"


class PostLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="uniq_post_like")
        ]


class PostComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    body = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
