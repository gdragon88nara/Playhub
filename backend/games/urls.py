from django.urls import path

from . import views

urlpatterns = [
    path("games", views.GameListCreateView.as_view(), name="game_list_create"),
    path("me/saved", views.SavedLibraryView.as_view(), name="saved_library"),
    path("games/<slug:slug>", views.GameDetailView.as_view(), name="game_detail"),
    path("games/<slug:slug>/bundle", views.GameBundleView.as_view(), name="game_bundle"),
    path("games/<slug:slug>/play", views.GamePlayView.as_view(), name="game_play"),
    path("games/<slug:slug>/like", views.LikeView.as_view(), name="game_like"),
    path("games/<slug:slug>/save", views.SaveView.as_view(), name="game_save"),
    path("games/<slug:slug>/comments", views.CommentListCreateView.as_view(),
         name="game_comments"),
]
