from rest_framework import serializers

from accounts.serializers import UserPublicSerializer
from .models import Comment, Game, SavedGame


class GameListSerializer(serializers.ModelSerializer):
    owner = UserPublicSerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Game
        fields = [
            "id", "slug", "title", "engine", "kind", "genre", "visibility", "status",
            "thumbnail", "is_paid", "price", "currency",
            "play_count", "likes_count", "owner", "created_at",
        ]


class GameDetailSerializer(serializers.ModelSerializer):
    owner = UserPublicSerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    play_url = serializers.CharField(read_only=True)
    is_liked_by_me = serializers.SerializerMethodField()
    is_saved_by_me = serializers.SerializerMethodField()
    scenes = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            "id", "slug", "title", "description", "engine", "kind", "genre", "visibility",
            "status", "entry_file", "thumbnail", "is_paid", "price", "currency",
            "play_count", "likes_count", "play_url", "owner",
            "is_liked_by_me", "is_saved_by_me", "scenes",
            "created_at", "deployed_at",
        ]

    def _me(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def get_is_liked_by_me(self, obj):
        me = self._me()
        return bool(me and obj.likes.filter(user=me).exists())

    def get_is_saved_by_me(self, obj):
        me = self._me()
        return bool(me and obj.saved_by.filter(user=me).exists())

    def get_scenes(self, obj):
        if obj.kind != Game.Kind.STORY:
            return []
        return [
            {"order": s.order, "title": s.title, "entry_file": s.entry_file}
            for s in obj.scenes.all()
        ]


class GameCreateSerializer(serializers.ModelSerializer):
    """Metadata for a new game. The bundle/files are handled in the view.
    ``thumbnail`` is an optional cover image uploaded alongside the game."""

    class Meta:
        model = Game
        fields = [
            "title", "description", "engine", "kind", "genre", "visibility",
            "is_paid", "price", "currency", "thumbnail",
        ]

    def validate(self, attrs):
        if attrs.get("is_paid") and attrs.get("price", 0) <= 0:
            raise serializers.ValidationError(
                {"price": "Paid games need a price greater than 0."}
            )
        return attrs


class CommentSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "user", "body", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class SavedGameSerializer(serializers.ModelSerializer):
    game = GameListSerializer(read_only=True)

    class Meta:
        model = SavedGame
        fields = ["id", "game", "created_at"]
