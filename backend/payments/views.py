from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import SellerProfile
from games.models import Game
from . import gateway
from .models import Purchase
from .serializers import PurchaseSerializer


class SellerOnboardingView(APIView):
    """POST /api/payments/onboarding — get a Connect onboarding link (seller)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_seller:
            raise ValidationError({"detail": "Only seller accounts can onboard."})
        profile, _ = SellerProfile.objects.get_or_create(user=request.user)
        return_url = request.data.get("return_url", "http://localhost:3000/settings/seller")
        return Response(gateway.create_onboarding_link(profile, return_url))


class CheckoutView(APIView):
    """POST /api/payments/checkout/<slug> — buy a paid game (split at provider)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        game = get_object_or_404(Game, slug=slug)
        if not game.is_paid:
            raise ValidationError({"detail": "This game is free."})
        if game.owner_id == request.user.id:
            raise ValidationError({"detail": "You already own this game."})
        if Purchase.has_access(request.user, game):
            raise ValidationError({"detail": "You already purchased this game."})

        success = request.data.get("success_url", f"http://localhost:3000/games/{slug}")
        cancel = request.data.get("cancel_url", f"http://localhost:3000/games/{slug}")
        purchase = gateway.create_checkout(request.user, game, success, cancel)
        return Response(PurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)


class ConfirmSimulatedView(APIView):
    """POST /api/payments/confirm/<purchase_id> — simulation-only: mark a
    simulated purchase paid (stands in for the Stripe webhook until keys exist)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        purchase = get_object_or_404(Purchase, pk=pk, buyer=request.user)
        if not purchase.simulated:
            raise ValidationError({"detail": "Real purchases are confirmed by the Stripe webhook."})
        purchase.status = Purchase.Status.PAID
        purchase.paid_at = timezone.now()
        purchase.save(update_fields=["status", "paid_at"])
        return Response(PurchaseSerializer(purchase).data)


class MyPurchasesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PurchaseSerializer

    def get_queryset(self):
        return Purchase.objects.filter(buyer=self.request.user).select_related("game")
