from django.urls import path

from . import views

urlpatterns = [
    path("payments/onboarding", views.SellerOnboardingView.as_view(), name="pay_onboarding"),
    path("payments/checkout/<slug:slug>", views.CheckoutView.as_view(), name="pay_checkout"),
    path("payments/confirm/<int:pk>", views.ConfirmSimulatedView.as_view(), name="pay_confirm"),
    path("payments/purchases", views.MyPurchasesView.as_view(), name="pay_purchases"),
]
