from rest_framework import serializers

from .models import Purchase


class PurchaseSerializer(serializers.ModelSerializer):
    game_title = serializers.CharField(source="game.title", read_only=True)
    game_slug = serializers.CharField(source="game.slug", read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id", "game_slug", "game_title", "amount", "currency",
            "commission_rate", "platform_fee", "seller_amount",
            "status", "simulated", "provider_session_id", "created_at", "paid_at",
        ]
