"""
Stripe Connect gateway.

Two modes:
* Configured  — real Stripe Connect calls (import stripe, use secret key). The
  checkout session sets ``application_fee_amount`` (our commission) and
  ``transfer_data.destination`` (the seller's connected account) so the split
  happens at the provider.
* Simulation  — no keys set. We compute the identical split and return a fake
  session id so the flow is fully exercisable without moving money.

The real branch is written but not executed here (no keys/SDK in this env); the
simulation branch is what the tests drive.
"""

from django.conf import settings

from .models import Purchase


def is_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def create_onboarding_link(seller_profile, return_url: str) -> dict:
    """Create a Stripe Connect onboarding link for a seller. Simulation returns
    a placeholder so the frontend flow works before keys exist."""
    if not is_configured():
        return {
            "mode": "simulation",
            "url": f"{return_url}?onboarding=simulated",
            "detail": "Stripe not configured; returning a simulated onboarding link.",
        }
    import stripe  # noqa: F401  (only imported when configured)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not seller_profile.provider_account_id:
        account = stripe.Account.create(type="express")
        seller_profile.provider = seller_profile.Provider.STRIPE
        seller_profile.provider_account_id = account.id
        seller_profile.save(update_fields=["provider", "provider_account_id"])
    link = stripe.AccountLink.create(
        account=seller_profile.provider_account_id,
        refresh_url=return_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return {"mode": "live", "url": link.url}


def create_checkout(buyer, game, success_url: str, cancel_url: str) -> Purchase:
    """Create a checkout for a paid game, splitting the platform commission from
    the seller payout. Returns a Purchase (pending, with the split recorded)."""
    seller = game.owner
    commission_rate = getattr(
        getattr(seller, "seller_profile", None), "commission_rate", settings.PLATFORM_COMMISSION_RATE
    )
    fee, seller_amount = Purchase.split(game.price, commission_rate)

    purchase = Purchase.objects.create(
        buyer=buyer, seller=seller, game=game,
        amount=game.price, currency=game.currency,
        commission_rate=commission_rate, platform_fee=fee, seller_amount=seller_amount,
        simulated=not is_configured(),
    )

    if not is_configured():
        purchase.provider_session_id = f"sim_{purchase.pk}"
        purchase.save(update_fields=["provider_session_id"])
        return purchase

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[{
            "price_data": {
                "currency": game.currency.lower(),
                "product_data": {"name": game.title},
                "unit_amount": int(game.price * 100),
            },
            "quantity": 1,
        }],
        payment_intent_data={
            "application_fee_amount": int(fee * 100),
            "transfer_data": {"destination": seller.seller_profile.provider_account_id},
        },
    )
    purchase.provider_session_id = session.id
    purchase.save(update_fields=["provider_session_id"])
    return purchase
