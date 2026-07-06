from django.contrib import admin

from .models import Purchase


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "seller", "game", "amount", "platform_fee",
                    "seller_amount", "status", "simulated", "created_at")
    list_filter = ("status", "simulated", "currency")
    search_fields = ("buyer__username", "seller__username", "game__title")
