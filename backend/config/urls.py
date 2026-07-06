"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from chat.media import serve_dm_media
from community.media import serve_post_media
from games.views import serve_game
from shorts.views import serve_short


def health(_request):
    return JsonResponse({"status": "ok", "service": "game-platform-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health, name="health"),
    path("api/", include("accounts.urls")),
    path("api/", include("games.urls")),
    path("api/", include("community.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("shorts.urls")),
    path("api/", include("ide.urls")),
    path("api/", include("payments.urls")),
    # Authenticated game bundle server (must precede the public media catch-all).
    # Files live in the protected root and require a signed play cookie.
    path("media/games/<int:game_id>/<path:path>", serve_game, name="serve_game"),
    # Signed-URL servers for post media & short-form videos (protected root).
    path("media/posts/<int:post_id>/<path:filename>", serve_post_media, name="serve_post_media"),
    path("media/shorts/<int:short_id>/v", serve_short, name="serve_short"),
    path("media/dm/<int:message_id>/file", serve_dm_media, name="serve_dm_media"),
]

if settings.DEBUG:
    # Public media only (avatars, thumbnails). Game bundles are NOT here.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
