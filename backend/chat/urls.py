from django.urls import path

from . import views

urlpatterns = [
    path("dm/threads", views.ThreadListView.as_view(), name="dm_threads"),
    path("dm/media", views.MyDmMediaView.as_view(), name="dm_media"),
    path("dm/threads/<int:pk>/messages", views.ThreadMessagesView.as_view(), name="dm_messages"),
    path("dm/threads/<int:pk>/attachments", views.ThreadAttachmentView.as_view(), name="dm_attachment"),
    path("dm/with/<str:username>", views.StartThreadView.as_view(), name="dm_start"),
    path("rooms", views.RoomListView.as_view(), name="rooms"),
    path("rooms/<slug:slug>/messages", views.RoomMessagesView.as_view(), name="room_messages"),
]
