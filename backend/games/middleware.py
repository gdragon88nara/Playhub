"""In-site-only enforcement for game bundles.

Games live entirely on this platform and must only be playable inside our own
frontend — never embedded on a third-party site. We serve the extracted bundle
under ``/media/games/`` and, for those responses, set a Content-Security-Policy
``frame-ancestors`` allow-list containing only our own frontend origin. Any
other site attempting to iframe the game is blocked by the browser.

We also drop the global ``X-Frame-Options: SAMEORIGIN`` header for these paths,
because our frontend runs on a different origin than the API during dev; the
CSP ``frame-ancestors`` directive (which browsers honour over X-Frame-Options)
is the precise, modern replacement.
"""

from django.conf import settings

GAME_MEDIA_PREFIX = f"{settings.MEDIA_URL}games/"


class GameEmbedPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        origins = " ".join(settings.GAME_FRAME_ANCESTORS)
        self.csp = f"frame-ancestors 'self' {origins}".strip()

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(GAME_MEDIA_PREFIX):
            response["Content-Security-Policy"] = self.csp
            response["X-Content-Type-Options"] = "nosniff"
            # Allow our cross-origin frontend to frame the game; the CSP above
            # still restricts *which* origins may do so. Marking the response
            # exempt stops XFrameOptionsMiddleware from re-adding DENY after us.
            response.xframe_options_exempt = True
            response.headers.pop("X-Frame-Options", None)
        return response
