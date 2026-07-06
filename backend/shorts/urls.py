from django.urls import path

from . import views

urlpatterns = [
    path("shorts", views.ShortListCreateView.as_view(), name="short_list_create"),
    path("shorts/<int:pk>", views.ShortDetailView.as_view(), name="short_detail"),
    path("shorts/<int:pk>/like", views.ShortLikeView.as_view(), name="short_like"),
]
