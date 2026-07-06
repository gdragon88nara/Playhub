from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/dm/<int:thread_id>/", consumers.DMConsumer.as_asgi()),
    path("ws/room/<slug:slug>/", consumers.RoomConsumer.as_asgi()),
    path("ws/voice/<slug:room>/", consumers.VoiceConsumer.as_asgi()),
]
