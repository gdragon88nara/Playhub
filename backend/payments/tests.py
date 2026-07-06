from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import SellerProfile
from games.models import Game
from .models import Purchase

User = get_user_model()
STRONG_PW = "Sup3rSecret!pw"


def make_user(email, username, **kw):
    return User.objects.create_user(email=email, username=username, password=STRONG_PW, **kw)


class SplitMathTests(APITestCase):
    def test_twenty_percent_split(self):
        fee, seller = Purchase.split("10.00", Decimal("0.20"))
        self.assertEqual(fee, Decimal("2.00"))
        self.assertEqual(seller, Decimal("8.00"))

    def test_rounding(self):
        fee, seller = Purchase.split("9.99", Decimal("0.20"))
        self.assertEqual(fee, Decimal("2.00"))            # 1.998 -> 2.00
        self.assertEqual(fee + seller, Decimal("9.99"))   # no money lost


class CheckoutFlowTests(APITestCase):
    def setUp(self):
        self.seller = make_user("s@t.com", "seller", is_seller=True)
        SellerProfile.objects.create(user=self.seller, commission_rate=Decimal("0.20"))
        self.buyer = make_user("b@t.com", "buyer")
        self.game = Game.objects.create(
            owner=self.seller, title="Paid Game", is_paid=True,
            price=Decimal("10.00"), currency="USD", status=Game.Status.DEPLOYED,
            entry_file="index.html",
        )

    def test_checkout_records_split_in_simulation(self):
        self.client.force_authenticate(self.buyer)
        res = self.client.post(f"/api/payments/checkout/{self.game.slug}")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["simulated"])
        self.assertEqual(Decimal(res.data["platform_fee"]), Decimal("2.00"))
        self.assertEqual(Decimal(res.data["seller_amount"]), Decimal("8.00"))
        self.assertEqual(res.data["status"], "pending")

    def test_confirm_grants_access(self):
        self.client.force_authenticate(self.buyer)
        pid = self.client.post(f"/api/payments/checkout/{self.game.slug}").data["id"]
        self.assertFalse(Purchase.has_access(self.buyer, self.game))
        confirm = self.client.post(f"/api/payments/confirm/{pid}")
        self.assertEqual(confirm.data["status"], "paid")
        self.game.refresh_from_db()
        self.assertTrue(Purchase.has_access(self.buyer, self.game))

    def test_free_game_checkout_rejected(self):
        free = Game.objects.create(owner=self.seller, title="Free", status=Game.Status.DEPLOYED)
        self.client.force_authenticate(self.buyer)
        res = self.client.post(f"/api/payments/checkout/{free.slug}")
        self.assertEqual(res.status_code, 400)

    def test_owner_cannot_buy_own_game(self):
        self.client.force_authenticate(self.seller)
        res = self.client.post(f"/api/payments/checkout/{self.game.slug}")
        self.assertEqual(res.status_code, 400)
