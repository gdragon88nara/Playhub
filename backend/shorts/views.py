import mimetypes

from django.core import signing
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Follow
from .models import Short, ShortLike
from .serializers import SHORT_SALT, ShortSerializer

MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB


class ShortListCreateView(generics.ListCreateAPIView):
    """GET /api/shorts — vertical feed (public + followed + own).
    POST /api/shorts — upload a short-form vertical video."""

    permission_classes = [IsAuthenticated]
    serializer_class = ShortSerializer

    def get_queryset(self):
        me = self.request.user
        if self.request.query_params.get("mine"):
            return Short.objects.filter(author=me).select_related("author")
        followed = Follow.objects.filter(follower=me).values_list("following_id", flat=True)
        public = Q(visibility=Short.Visibility.PUBLIC, author__is_private=False)
        followed_q = Q(author_id__in=followed) & ~Q(visibility=Short.Visibility.PRIVATE)
        return (
            Short.objects.filter(public | followed_q | Q(author=me))
            .select_related("author")
            .distinct()
        )

    def create(self, request, *args, **kwargs):
        video = request.FILES.get("video")
        if not video:
            raise ValidationError({"video": "A video file is required."})
        if not (video.content_type or "").lower().startswith("video/"):
            raise ValidationError({"video": "File must be a video."})
        if video.size > MAX_VIDEO_BYTES:
            raise ValidationError({"video": "Video must be under 200 MB."})

        short = Short.objects.create(
            author=request.user,
            caption=request.data.get("caption", "").strip(),
            visibility=request.data.get("visibility", Short.Visibility.PUBLIC),
            video=video,
        )
        return Response(
            ShortSerializer(short, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ShortDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ShortSerializer

    def get_object(self):
        short = get_object_or_404(Short.objects.select_related("author"), pk=self.kwargs["pk"])
        if self.request.method == "DELETE":
            if short.author_id != self.request.user.id:
                raise PermissionDenied("Not your short.")
        elif not short.visible_to(self.request.user):
            raise PermissionDenied("You cannot view this short.")
        return short


class ShortLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        short = _visible_or_404(request, pk)
        ShortLike.objects.get_or_create(user=request.user, short=short)
        return Response({"liked": True, "likes_count": short.likes_count})

    def delete(self, request, pk):
        short = _visible_or_404(request, pk)
        ShortLike.objects.filter(user=request.user, short=short).delete()
        return Response({"liked": False, "likes_count": short.likes_count})


def _visible_or_404(request, pk) -> Short:
    short = get_object_or_404(Short.objects.select_related("author"), pk=pk)
    if not short.visible_to(request.user):
        raise PermissionDenied("You cannot access this short.")
    return short


def serve_short(request, short_id: int):
    """Stream a short's video after validating its signed token. The stored path
    comes from the DB (no user-supplied path), so there is no traversal risk."""
    token = request.GET.get("t", "")
    try:
        data = signing.loads(token, salt=SHORT_SALT, max_age=60 * 60 * 6)
        if data.get("s") != short_id:
            raise signing.BadSignature("mismatch")
    except signing.BadSignature:
        return HttpResponseForbidden("Invalid or expired media link.")

    short = get_object_or_404(Short, pk=short_id)
    try:
        f = short.video.open("rb")
    except FileNotFoundError:
        raise Http404("Not found")
    ctype, _ = mimetypes.guess_type(short.video.name)
    resp = FileResponse(f, content_type=ctype or "video/mp4")
    resp["Accept-Ranges"] = "bytes"
    return resp
