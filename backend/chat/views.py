from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from .media import signed_dm_url
from .models import ChatRoom, DirectMessage, DirectThread, RoomMessage
from .serializers import (
    ChatRoomSerializer,
    DirectMessageSerializer,
    DirectThreadSerializer,
    RoomMessageSerializer,
)

MAX_ATTACHMENT_BYTES = 50 * 1024 * 1024  # 50 MB per DM attachment

DEFAULT_ROOMS = [
    ("lobby", "Lobby", "The main open chat for everyone."),
    ("games", "Games", "Talk about games and share what you're playing."),
    ("dev", "Dev", "Game development, code, and the in-browser IDE."),
]


def ensure_default_rooms():
    for slug, name, desc in DEFAULT_ROOMS:
        ChatRoom.objects.get_or_create(slug=slug, defaults={"name": name, "description": desc})


class ThreadListView(generics.ListAPIView):
    """GET /api/dm/threads — my DM conversations."""

    permission_classes = [IsAuthenticated]
    serializer_class = DirectThreadSerializer

    def get_queryset(self):
        return DirectThread.for_user(self.request.user).select_related("user_a", "user_b")


class StartThreadView(APIView):
    """POST /api/dm/with/<username> — get or create the DM thread with a user."""

    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        other = get_object_or_404(User, username=username)
        if other == request.user:
            raise ValidationError({"detail": "Cannot DM yourself."})
        thread, _ = DirectThread.get_or_create_between(request.user, other)
        return Response(
            DirectThreadSerializer(thread, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class ThreadMessagesView(generics.ListAPIView):
    """GET /api/dm/threads/<id>/messages — history (participants only)."""

    permission_classes = [IsAuthenticated]
    serializer_class = DirectMessageSerializer

    def get_queryset(self):
        thread = get_object_or_404(DirectThread, pk=self.kwargs["pk"])
        if not thread.has_participant(self.request.user):
            raise PermissionDenied("Not your thread.")
        return thread.messages.select_related("sender")


class ThreadAttachmentView(APIView):
    """POST /api/dm/threads/<id>/attachments — send an image/file in a DM."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        thread = get_object_or_404(DirectThread, pk=pk)
        if not thread.has_participant(request.user):
            raise PermissionDenied("Not your thread.")
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "No file uploaded."})
        if upload.size > MAX_ATTACHMENT_BYTES:
            raise ValidationError({"file": "Attachment must be under 50 MB."})

        ct = (upload.content_type or "").lower()
        kind = (DirectMessage.AttachmentType.IMAGE if ct.startswith("image/")
                else DirectMessage.AttachmentType.FILE)
        msg = DirectMessage.objects.create(
            thread=thread, sender=request.user, body=request.data.get("body", ""),
            attachment=upload, attachment_name=upload.name, attachment_type=kind,
        )
        thread.last_message_at = timezone.now()
        thread.save(update_fields=["last_message_at"])
        return Response(
            DirectMessageSerializer(msg, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MyDmMediaView(APIView):
    """GET /api/dm/media — every attachment across my DM threads (a media hub)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user
        threads = DirectThread.for_user(me)
        msgs = (
            DirectMessage.objects.filter(thread__in=threads)
            .exclude(attachment="")
            .exclude(attachment__isnull=True)
            .select_related("sender", "thread", "thread__user_a", "thread__user_b")
            .order_by("-created_at")[:200]
        )
        items = []
        for m in msgs:
            other = m.thread.other(me)
            items.append({
                "id": m.id,
                "thread_id": m.thread_id,
                "url": signed_dm_url(m, me),
                "name": m.attachment_name,
                "attachment_type": m.attachment_type,
                "from_me": m.sender_id == me.id,
                "sender": m.sender.username,
                "other": other.username,
                "created_at": m.created_at,
            })
        return Response(items)


class RoomListView(generics.ListAPIView):
    """GET /api/rooms — open realtime rooms."""

    permission_classes = [IsAuthenticated]
    serializer_class = ChatRoomSerializer

    def get_queryset(self):
        ensure_default_rooms()
        return ChatRoom.objects.all()


class RoomMessagesView(generics.ListAPIView):
    """GET /api/rooms/<slug>/messages — recent history for an open room."""

    permission_classes = [IsAuthenticated]
    serializer_class = RoomMessageSerializer

    def get_queryset(self):
        room = get_object_or_404(ChatRoom, slug=self.kwargs["slug"])
        return (
            RoomMessage.objects.filter(room=room)
            .select_related("sender")
            .order_by("created_at")[:200]
        )
