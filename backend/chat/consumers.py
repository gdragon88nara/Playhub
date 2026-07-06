"""WebSocket consumers for realtime DM and open chat rooms."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from .models import ChatRoom, DirectMessage, DirectThread, RoomMessage


class DMConsumer(AsyncJsonWebsocketConsumer):
    """ws/dm/<thread_id>/ — 1:1 direct messages. Only the two participants may
    connect."""

    async def connect(self):
        self.user = self.scope["user"]
        self.thread_id = int(self.scope["url_route"]["kwargs"]["thread_id"])
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.thread = await self._get_thread()
        if self.thread is None:
            await self.close(code=4403)
            return
        self.group = f"dm_{self.thread_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content):
        body = (content.get("body") or "").strip()
        if not body:
            return
        msg = await self._save(body)
        await self.channel_layer.group_send(
            self.group,
            {
                "type": "chat.message",
                "id": msg.id,
                "body": msg.body,
                "sender": self.user.username,
                "sender_id": self.user.id,
                "created_at": msg.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"})

    @database_sync_to_async
    def _get_thread(self):
        try:
            t = DirectThread.objects.get(pk=self.thread_id)
        except DirectThread.DoesNotExist:
            return None
        return t if t.has_participant(self.user) else None

    @database_sync_to_async
    def _save(self, body):
        msg = DirectMessage.objects.create(thread=self.thread, sender=self.user, body=body)
        DirectThread.objects.filter(pk=self.thread_id).update(last_message_at=timezone.now())
        return msg


class RoomConsumer(AsyncJsonWebsocketConsumer):
    """ws/room/<slug>/ — open public realtime room."""

    async def connect(self):
        self.user = self.scope["user"]
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.room = await self._get_room()
        if self.room is None:
            await self.close(code=4404)
            return
        self.group = f"room_{self.slug}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content):
        body = (content.get("body") or "").strip()
        if not body:
            return
        msg = await self._save(body)
        await self.channel_layer.group_send(
            self.group,
            {
                "type": "chat.message",
                "id": msg.id,
                "body": msg.body,
                "sender": self.user.username,
                "sender_id": self.user.id,
                "created_at": msg.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"})

    @database_sync_to_async
    def _get_room(self):
        return ChatRoom.objects.filter(slug=self.slug).first()

    @database_sync_to_async
    def _save(self, body):
        return RoomMessage.objects.create(room=self.room, sender=self.user, body=body)


class VoiceConsumer(AsyncJsonWebsocketConsumer):
    """ws/voice/<room>/ — WebRTC signalling for Discord-style voice.

    This relays SDP offers/answers and ICE candidates between peers (a P2P mesh
    — high audio quality for small groups) and broadcasts join/leave presence.
    The actual audio flows peer-to-peer over WebRTC, so the call keeps running
    independent of page navigation once the frontend holds the PeerConnection at
    the app-shell level. Large group calls should add an SFU (LiveKit/mediasoup)
    that plugs into this same signalling."""

    async def connect(self):
        self.user = self.scope["user"]
        self.room = self.scope["url_route"]["kwargs"]["room"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.group = f"voice_{self.room}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        # Announce presence so existing peers can initiate a connection.
        await self.channel_layer.group_send(
            self.group,
            {"type": "voice.signal", "event": "peer-join",
             "peer": self.user.username, "peer_id": self.user.id,
             "channel": self.channel_name},
        )

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_send(
                self.group,
                {"type": "voice.signal", "event": "peer-leave",
                 "peer": self.user.username, "peer_id": self.user.id,
                 "channel": self.channel_name},
            )
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content):
        # Relay signalling payloads (offer/answer/ice) to the room.
        event = content.get("event")
        if event not in ("offer", "answer", "ice"):
            return
        await self.channel_layer.group_send(
            self.group,
            {
                "type": "voice.signal",
                "event": event,
                "peer": self.user.username,
                "peer_id": self.user.id,
                "channel": self.channel_name,
                "target": content.get("target"),
                "data": content.get("data"),
            },
        )

    async def voice_signal(self, event):
        # Don't echo a peer's own message back to itself.
        if event.get("channel") == self.channel_name:
            return
        payload = {k: v for k, v in event.items() if k not in ("type", "channel")}
        await self.send_json(payload)
