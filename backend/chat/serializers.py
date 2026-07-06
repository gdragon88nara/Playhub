from rest_framework import serializers

from accounts.serializers import UserPublicSerializer
from .media import signed_dm_url
from .models import ChatRoom, DirectMessage, DirectThread, RoomMessage


class DirectMessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.username", read_only=True)
    sender_id = serializers.IntegerField(read_only=True)
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = DirectMessage
        fields = [
            "id", "sender", "sender_id", "body", "created_at",
            "attachment_url", "attachment_name", "attachment_type",
        ]

    def get_attachment_url(self, obj):
        request = self.context.get("request")
        if not obj.attachment or not request:
            return None
        return signed_dm_url(obj, request.user)


class DirectThreadSerializer(serializers.ModelSerializer):
    other = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = DirectThread
        fields = ["id", "other", "last_message", "last_message_at", "created_at"]

    def get_other(self, obj):
        me = self.context["request"].user
        return UserPublicSerializer(obj.other(me), context=self.context).data

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        return msg.body if msg else ""


class RoomMessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.username", read_only=True)
    sender_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = RoomMessage
        fields = ["id", "sender", "sender_id", "body", "created_at"]


class ChatRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ["id", "slug", "name", "description"]
