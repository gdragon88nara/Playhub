from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Block, Follow, FollowRequest, Report, SellerProfile

User = get_user_model()


class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = [
            "business_display_name", "country", "provider",
            "onboarding_status", "payouts_enabled", "commission_rate",
        ]
        # These are set by provider webhooks / server logic, never by the client.
        read_only_fields = [
            "provider", "onboarding_status", "payouts_enabled", "commission_rate",
        ]


class UserPublicSerializer(serializers.ModelSerializer):
    """Safe public view of a user (no email)."""

    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_followed_by_me = serializers.SerializerMethodField()
    follow_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "display_name", "bio", "avatar",
            "is_private", "is_seller", "followers_count", "following_count",
            "is_followed_by_me", "follow_status", "date_joined",
        ]

    def _me(self):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user
        return None

    def get_is_followed_by_me(self, obj):
        me = self._me()
        return bool(me and me.is_following(obj))

    def get_follow_status(self, obj):
        """One of: self | following | requested | none — drives the follow button."""
        me = self._me()
        if not me:
            return "none"
        if me.pk == obj.pk:
            return "self"
        if me.is_following(obj):
            return "following"
        if FollowRequest.objects.filter(
            requester=me, target=obj, status=FollowRequest.Status.PENDING
        ).exists():
            return "requested"
        return "none"


class MeSerializer(serializers.ModelSerializer):
    """Full view of the authenticated user (includes email + seller profile)."""

    seller_profile = SellerProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "display_name", "bio", "avatar",
            "is_private", "is_seller", "seller_profile", "date_joined",
            "last_active", "notify_follows", "notify_likes", "notify_comments",
        ]
        read_only_fields = ["id", "email", "is_seller", "date_joined", "last_active"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    become_seller = serializers.BooleanField(write_only=True, default=False)

    class Meta:
        model = User
        fields = [
            "email", "username", "display_name", "password",
            "is_private", "become_seller",
        ]

    def validate_email(self, value):
        return value.lower()

    def create(self, validated_data):
        become_seller = validated_data.pop("become_seller", False)
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password, is_seller=become_seller, **validated_data
        )
        if become_seller:
            # Empty shell; real payout details are collected later via the
            # provider's hosted onboarding — we never store raw financial data.
            SellerProfile.objects.create(user=user)
        return user


class FollowRequestSerializer(serializers.ModelSerializer):
    requester = UserPublicSerializer(read_only=True)

    class Meta:
        model = FollowRequest
        fields = ["id", "requester", "status", "created_at"]


class BlockSerializer(serializers.ModelSerializer):
    blocked = UserPublicSerializer(read_only=True)

    class Meta:
        model = Block
        fields = ["id", "blocked", "created_at"]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "kind", "target", "reason", "note", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]
