from django.urls import path

from . import views

urlpatterns = [
    path("posts", views.PostListCreateView.as_view(), name="post_list_create"),
    path("posts/<int:pk>", views.PostDetailView.as_view(), name="post_detail"),
    path("posts/<int:pk>/like", views.PostLikeView.as_view(), name="post_like"),
    path("posts/<int:pk>/comments", views.PostCommentListCreateView.as_view(),
         name="post_comments"),
]
