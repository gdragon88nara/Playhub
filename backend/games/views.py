import mimetypes
import os
import shutil

from django.conf import settings
from django.core import signing
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Follow
from .bundle import BundleError, extract_bundle, save_files
from .models import Comment, Game, Like, SavedGame
from .serializers import (
    CommentSerializer,
    GameCreateSerializer,
    GameDetailSerializer,
    GameListSerializer,
    SavedGameSerializer,
)


def visible_games_qs(viewer):
    """Games the viewer is allowed to see: deployed public, deployed
    followers-only from accounts they follow, plus all of their own."""
    followed_ids = Follow.objects.filter(follower=viewer).values_list("following_id", flat=True)
    deployed = Q(status=Game.Status.DEPLOYED)
    public = Q(visibility=Game.Visibility.PUBLIC) & Q(owner__is_private=False)
    followed = Q(owner_id__in=followed_ids) & ~Q(visibility=Game.Visibility.PRIVATE)
    return (
        Game.objects.filter((deployed & (public | followed)) | Q(owner=viewer))
        .select_related("owner")
        .distinct()
    )


class GameListCreateView(generics.ListAPIView):
    """GET /api/games — feed (?owner=<handle>, ?mine=1).
    POST /api/games — create a game; if a ``bundle`` ZIP is attached it is
    extracted and the game is deployed immediately (the Deploy button)."""

    permission_classes = [IsAuthenticated]
    serializer_class = GameListSerializer

    def get_queryset(self):
        qs = visible_games_qs(self.request.user)
        owner = self.request.query_params.get("owner")
        if owner:
            qs = qs.filter(owner__username=owner)
        if self.request.query_params.get("mine"):
            qs = qs.filter(owner=self.request.user)
        genre = self.request.query_params.get("genre")
        if genre:
            qs = qs.filter(genre=genre)
        return qs

    def post(self, request, *args, **kwargs):
        meta = GameCreateSerializer(data=request.data)
        meta.is_valid(raise_exception=True)
        game = Game(owner=request.user, **meta.validated_data)
        game.save()

        # Roll back the empty draft if the (first) upload is invalid.
        _apply_upload(request, game, rollback=True)

        return Response(
            GameDetailSerializer(game, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


PLAY_SALT = "games.play-access"


def _play_cookie_name(game_id: int) -> str:
    return f"gp_play_{game_id}"


def _mark_deployed(game: Game, entry: str):
    game.entry_file = entry
    game.status = Game.Status.DEPLOYED
    game.deployed_at = timezone.now()
    game.save(update_fields=["entry_file", "status", "deployed_at", "updated_at"])


def _run_extractor(game: Game, extractor, rollback: bool):
    """Run ``extractor(dest) -> entry`` and finalise the deploy. On failure roll
    back only when ``rollback`` (a freshly created draft), never an existing game."""
    try:
        entry = extractor(str(game.bundle_abs))
    except BundleError as exc:
        if rollback:
            game.delete()
        raise ValidationError({"bundle": str(exc)})
    _mark_deployed(game, entry)


def _upload_entries(request):
    """Zip ``files``/``paths`` from a direct file/folder upload into
    ``(relative_path, uploaded_file)`` pairs, or ``None`` if none were sent."""
    files = request.FILES.getlist("files")
    if not files:
        return None
    paths = request.data.getlist("paths") if hasattr(request.data, "getlist") else []
    if len(paths) == len(files):
        return list(zip(paths, files))
    return [(f.name, f) for f in files]


def _apply_upload(request, game: Game, *, rollback: bool):
    """Deploy from a direct file/folder upload (preferred) or a legacy ``.zip``.
    Leaves the game as a draft when nothing was uploaded (create only)."""
    entries = _upload_entries(request)
    if entries is not None:
        _run_extractor(game, lambda dest: save_files(entries, dest), rollback)
        return True
    bundle = request.FILES.get("bundle")
    if bundle:
        _run_extractor(game, lambda dest: extract_bundle(bundle, dest), rollback)
        return True
    return False


class GameDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/games/<slug>."""

    permission_classes = [IsAuthenticated]
    serializer_class = GameDetailSerializer
    lookup_field = "slug"

    def get_object(self):
        game = get_object_or_404(Game.objects.select_related("owner"), slug=self.kwargs["slug"])
        if self.request.method in ("PATCH", "PUT", "DELETE"):
            if game.owner_id != self.request.user.id:
                raise PermissionDenied("Not your game.")
        elif not game.visible_to(self.request.user):
            raise PermissionDenied("You cannot view this game.")
        return game

    def perform_destroy(self, instance):
        bundle_abs = instance.bundle_abs
        instance.delete()
        shutil.rmtree(bundle_abs, ignore_errors=True)


class GameBundleView(APIView):
    """POST /api/games/<slug>/bundle — (re)upload files/folder (or a .zip) & deploy.

    On failure the existing game is preserved (never rolled back)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        game = get_object_or_404(Game, slug=slug)
        if game.owner_id != request.user.id:
            raise PermissionDenied("Not your game.")
        if not _apply_upload(request, game, rollback=False):
            raise ValidationError({"bundle": "No files uploaded."})
        return Response(GameDetailSerializer(game, context={"request": request}).data)


class GamePlayView(APIView):
    """POST /api/games/<slug>/play — authorise a play session.

    Verifies visibility, bumps the play count, and sets a short-lived signed
    cookie scoped to this game's serve path. The sandboxed iframe then loads the
    bundle from the authenticated serve view, which requires that cookie — so a
    game can only be played from inside the site, never by a direct/hotlinked
    URL, and private games stay private."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        game = get_object_or_404(Game.objects.select_related("owner"), slug=slug)
        if not game.visible_to(request.user):
            raise PermissionDenied("You cannot play this game.")
        if game.status != Game.Status.DEPLOYED:
            raise ValidationError({"detail": "Game is not deployed yet."})
        Game.objects.filter(pk=game.pk).update(play_count=game.play_count + 1)

        token = signing.dumps({"g": game.pk, "u": request.user.pk}, salt=PLAY_SALT)
        resp = Response({"play_url": game.play_url})
        resp.set_cookie(
            _play_cookie_name(game.pk), token,
            max_age=settings.PLAY_COOKIE_MAX_AGE,
            path=f"{settings.MEDIA_URL}games/{game.pk}/",
            samesite="Lax", secure=not settings.DEBUG, httponly=True,
        )
        return resp


# -- Authenticated static server for game bundles (Python, not nginx) ---------
_ENCODINGS = {".br": "br", ".gz": "gzip"}


def serve_game(request, game_id: int, path: str):
    """Stream a file from a game's protected bundle after checking the signed
    play cookie. Mounted at ``/media/games/<id>/<path>`` — the embed policy
    middleware adds the frame-ancestors CSP to these responses."""
    game = get_object_or_404(Game, pk=game_id)

    token = request.COOKIES.get(_play_cookie_name(game_id))
    try:
        data = signing.loads(token or "", salt=PLAY_SALT, max_age=settings.PLAY_COOKIE_MAX_AGE)
        if data.get("g") != game_id:
            raise signing.BadSignature("game mismatch")
    except signing.BadSignature:
        return HttpResponseForbidden("Play session required. Open the game from the site.")

    base = os.path.abspath(game.bundle_abs)
    full = os.path.abspath(os.path.join(base, path))
    if os.path.commonpath([base]) != os.path.commonpath([base, full]) or not os.path.isfile(full):
        raise Http404("Not found")

    # Content type (+ content-encoding for pre-compressed Unity assets).
    ext = os.path.splitext(full)[1].lower()
    encoding = _ENCODINGS.get(ext)
    guess_name = full[: -len(ext)] if encoding else full
    ctype, _ = mimetypes.guess_type(guess_name)
    if guess_name.endswith(".wasm"):
        ctype = "application/wasm"
    resp = FileResponse(open(full, "rb"), content_type=ctype or "application/octet-stream")
    if encoding:
        resp["Content-Encoding"] = encoding
    return resp


class LikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        game = _visible_or_404(request, slug)
        Like.objects.get_or_create(user=request.user, game=game)
        return Response({"liked": True, "likes_count": game.likes_count})

    def delete(self, request, slug):
        game = _visible_or_404(request, slug)
        Like.objects.filter(user=request.user, game=game).delete()
        return Response({"liked": False, "likes_count": game.likes_count})


class SaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        game = _visible_or_404(request, slug)
        SavedGame.objects.get_or_create(user=request.user, game=game)
        return Response({"saved": True})

    def delete(self, request, slug):
        game = _visible_or_404(request, slug)
        SavedGame.objects.filter(user=request.user, game=game).delete()
        return Response({"saved": False})


class CommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def get_queryset(self):
        game = _visible_or_404(self.request, self.kwargs["slug"])
        return game.comments.select_related("user")

    def perform_create(self, serializer):
        game = _visible_or_404(self.request, self.kwargs["slug"])
        serializer.save(user=self.request.user, game=game)


class SavedLibraryView(generics.ListAPIView):
    """GET /api/me/saved — the current user's saved-game library."""

    permission_classes = [IsAuthenticated]
    serializer_class = SavedGameSerializer

    def get_queryset(self):
        return SavedGame.objects.filter(user=self.request.user).select_related("game", "game__owner")


def _visible_or_404(request, slug) -> Game:
    game = get_object_or_404(Game.objects.select_related("owner"), slug=slug)
    if not game.visible_to(request.user):
        raise PermissionDenied("You cannot access this game.")
    return game
