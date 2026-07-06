"""
Realtime chat domain.

* DirectThread / DirectMessage — 1:1 DM between two users.
* ChatRoom / RoomMessage       — open realtime rooms (a shared live board).

Message delivery is realtime over WebSocket (Channels); these models persist
history so clients can load prior messages and reconnect.
"""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Q
from django.utils.deconstruct import deconstructible


@deconstructible
class ProtectedDMStorage(FileSystemStorage):
    """DM attachments live in the protected root and are reachable only through
    the signed-URL serve view (never a bare public URL)."""

    @property
    def base_location(self):
        return str(settings.DM_ROOT)

    @property
    def location(self):
        return os.path.abspath(str(settings.DM_ROOT))


protected_dm_storage = ProtectedDMStorage()


def dm_attachment_path(instance, filename):
    return f"{instance.thread_id}/{filename}"


class DirectThread(models.Model):
    """A 1:1 conversation. Exactly two participants; the (user_a, user_b) pair is
    stored order-normalised (user_a.id < user_b.id) so it is unique."""

    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_a"
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_b"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="uniq_direct_thread"),
        ]
        ordering = ["-last_message_at", "-created_at"]

    @staticmethod
    def normalized_pair(u1, u2):
        return (u1, u2) if u1.id < u2.id else (u2, u1)

    @classmethod
    def get_or_create_between(cls, u1, u2):
        a, b = cls.normalized_pair(u1, u2)
        return cls.objects.get_or_create(user_a=a, user_b=b)

    @classmethod
    def for_user(cls, user):
        return cls.objects.filter(Q(user_a=user) | Q(user_b=user))

    def has_participant(self, user) -> bool:
        return user.id in (self.user_a_id, self.user_b_id)

    def other(self, user):
        return self.user_b if user.id == self.user_a_id else self.user_a


class DirectMessage(models.Model):
    class AttachmentType(models.TextChoices):
        IMAGE = "image", "Image"
        FILE = "file", "File"

    thread = models.ForeignKey(DirectThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(max_length=4000, blank=True)
    attachment = models.FileField(
        upload_to=dm_attachment_path, storage=protected_dm_storage, blank=True, null=True
    )
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_type = models.CharField(
        max_length=8, choices=AttachmentType.choices, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["thread", "created_at"])]


class ChatRoom(models.Model):
    """An open, public realtime room (live board)."""

    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"#{self.slug}"


class RoomMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["room", "created_at"])]
