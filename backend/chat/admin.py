from django.contrib import admin

from .models import ChatRoom, DirectMessage, DirectThread, RoomMessage


@admin.register(DirectThread)
class DirectThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "user_a", "user_b", "last_message_at")


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(DirectMessage)
admin.site.register(RoomMessage)
