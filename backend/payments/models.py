"""
Marketplace payments (Phase 7 — structural).

The platform never holds funds: at checkout the payment provider (Stripe
Connect) charges the buyer and splits the money, routing the platform's
commission (default 20%) to us and the remainder to the seller's connected
account. We store only the split breakdown and provider references — never raw
card/bank data.

Until real API keys are configured the gateway runs in "simulation" mode: it
computes and records the exact split so the whole flow is testable, without
moving money.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models


def _money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Purchase(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales"
    )
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="purchases")

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    seller_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=16, default="stripe")
    provider_session_id = models.CharField(max_length=255, blank=True)
    simulated = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["buyer", "game"])]

    def __str__(self):
        return f"Purchase(@{self.buyer.username} -> {self.game_id}, {self.status})"

    @staticmethod
    def split(amount, commission_rate):
        """Return (platform_fee, seller_amount) for an amount + commission rate."""
        amount = _money(amount)
        fee = _money(amount * Decimal(str(commission_rate)))
        return fee, _money(amount - fee)

    @classmethod
    def has_access(cls, user, game) -> bool:
        """A paid game is playable by its owner or anyone who has paid for it."""
        if not game.is_paid:
            return True
        if user.is_authenticated and user.pk == game.owner_id:
            return True
        return cls.objects.filter(buyer=user, game=game, status=cls.Status.PAID).exists()
