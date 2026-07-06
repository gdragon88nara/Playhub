from rest_framework import serializers

from accounts.serializers import UserPublicSerializer
from .media import signed_media_url
from .models import Post, PostComment, PostMedia


class PostMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PostMedia
        fields = ["id", "media_type", "url", "order"]

    def get_url(self, obj):
        return signed_media_url(obj)


class PostSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    media = PostMediaSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "author", "body", "visibility", "media",
            "likes_count", "comments_count", "is_liked_by_me", "created_at",
        ]

    def get_is_liked_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()


class PostCommentSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = PostComment
        fields = ["id", "user", "body", "created_at"]
        read_only_fields = ["id", "user", "created_at"]
