from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    # Auth
    path("auth/register", views.RegisterView.as_view(), name="register"),
    path("auth/login", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    # Search
    path("search", views.SearchView.as_view(), name="search"),
    # Me
    path("me", views.MeView.as_view(), name="me"),
    path("me/activity", views.MyActivityView.as_view(), name="me_activity"),
    path("me/notifications", views.NotificationsView.as_view(), name="me_notifications"),
    path("me/comments", views.MyCommentsView.as_view(), name="me_comments"),
    path("me/favorites", views.MyFavoritesView.as_view(), name="me_favorites"),
    # Safety
    path("blocks", views.BlockListView.as_view(), name="blocks"),
    path("blocks/<str:username>", views.BlockView.as_view(), name="block"),
    path("reports", views.ReportCreateView.as_view(), name="reports"),
    # Follow requests (must precede the <username> catch-all)
    path("follow-requests", views.IncomingFollowRequestsView.as_view(),
         name="follow_requests"),
    path("follow-requests/<int:pk>/<str:action>",
         views.FollowRequestActionView.as_view(), name="follow_request_action"),
    # Users
    path("users/<str:username>", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<str:username>/follow", views.FollowView.as_view(), name="follow"),
    path("users/<str:username>/<str:which>", views.FollowListView.as_view(),
         name="follow_list"),
]
