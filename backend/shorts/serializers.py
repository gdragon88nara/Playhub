from django.conf import settings
from django.core import signing
from rest_framework import serializers

from accounts.serializers import UserPublicSerializer
from .models import Short

SHORT_SALT = "shorts.video"


def signed_short_url(short) -> str:
    token = signing.dumps({"s": short.id}, salt=SHORT_SALT)
    return f"{settings.MEDIA_URL}shorts/{short.id}/v?t={token}"


class ShortSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    video_url = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Short
        fields = [
            "id", "author", "caption", "visibility", "video_url",
            "view_count", "likes_count", "is_liked_by_me", "created_at",
        ]

    def get_video_url(self, obj):
        return signed_short_url(obj)

    def get_is_liked_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()
