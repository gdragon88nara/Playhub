"""JWT authentication for WebSocket connections.

Browsers cannot set Authorization headers on a WebSocket handshake, so the
client passes its access token as ``?token=<jwt>``. This middleware validates it
and puts the user on the connection scope."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def _get_user(user_id):
    try:
        return User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = None
        qs = parse_qs(scope.get("query_string", b"").decode())
        if "token" in qs:
            token = qs["token"][0]

        scope["user"] = AnonymousUser()
        if token:
            try:
                access = AccessToken(token)
                scope["user"] = await _get_user(access["user_id"])
            except (TokenError, KeyError):
                pass

        return await super().__call__(scope, receive, send)
