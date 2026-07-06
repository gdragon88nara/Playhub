from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Follow
from .models import Post, PostLike, PostMedia
from .serializers import PostCommentSerializer, PostSerializer

MAX_MEDIA_PER_POST = 10
MAX_MEDIA_BYTES = 100 * 1024 * 1024  # 100 MB per file


def _media_type(uploaded):
    ct = (uploaded.content_type or "").lower()
    if ct.startswith("image/"):
        return PostMedia.MediaType.IMAGE
    if ct.startswith("video/"):
        return PostMedia.MediaType.VIDEO
    return None


class PostListCreateView(generics.ListCreateAPIView):
    """GET /api/posts — timeline (following + you) by default;
    ``?user=<handle>`` for a profile; ``?feed=explore`` for public discovery.
    POST /api/posts — create a post with optional image/video media."""

    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        me = self.request.user
        base = Post.objects.select_related("author").prefetch_related("media", "likes")

        user = self.request.query_params.get("user")
        if user:
            # A single profile's posts, filtered by per-post visibility below.
            qs = base.filter(author__username=user)
            return [p for p in qs if p.visible_to(me)]

        if self.request.query_params.get("feed") == "explore":
            return base.filter(
                visibility=Post.Visibility.PUBLIC, author__is_private=False
            )

        # Default timeline: people you follow (non-private posts) + your own.
        followed_ids = Follow.objects.filter(follower=me).values_list("following_id", flat=True)
        return base.filter(
            (Q(author_id__in=followed_ids) & ~Q(visibility=Post.Visibility.PRIVATE))
            | Q(author=me)
        ).distinct()

    def create(self, request, *args, **kwargs):
        files = request.FILES.getlist("media")
        if len(files) > MAX_MEDIA_PER_POST:
            raise ValidationError({"media": f"At most {MAX_MEDIA_PER_POST} files."})

        body = request.data.get("body", "").strip()
        if not body and not files:
            raise ValidationError({"detail": "A post needs text or media."})

        visibility = request.data.get("visibility", Post.Visibility.PUBLIC)
        post = Post.objects.create(author=request.user, body=body, visibility=visibility)

        for i, f in enumerate(files):
            mtype = _media_type(f)
            if mtype is None:
                post.delete()
                raise ValidationError({"media": f"Unsupported file type: {f.content_type}"})
            if f.size > MAX_MEDIA_BYTES:
                post.delete()
                raise ValidationError({"media": "Each file must be under 100 MB."})
            PostMedia.objects.create(post=post, media_type=mtype, file=f, order=i)

        return Response(
            PostSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class PostDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_object(self):
        post = get_object_or_404(
            Post.objects.select_related("author").prefetch_related("media", "likes"),
            pk=self.kwargs["pk"],
        )
        if self.request.method == "DELETE":
            if post.author_id != self.request.user.id:
                raise PermissionDenied("Not your post.")
        elif not post.visible_to(self.request.user):
            raise PermissionDenied("You cannot view this post.")
        return post


class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = _visible_or_404(request, pk)
        PostLike.objects.get_or_create(user=request.user, post=post)
        return Response({"liked": True, "likes_count": post.likes_count})

    def delete(self, request, pk):
        post = _visible_or_404(request, pk)
        PostLike.objects.filter(user=request.user, post=post).delete()
        return Response({"liked": False, "likes_count": post.likes_count})


class PostCommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostCommentSerializer

    def get_queryset(self):
        post = _visible_or_404(self.request, self.kwargs["pk"])
        return post.comments.select_related("user")

    def perform_create(self, serializer):
        post = _visible_or_404(self.request, self.kwargs["pk"])
        serializer.save(user=self.request.user, post=post)


def _visible_or_404(request, pk) -> Post:
    post = get_object_or_404(Post.objects.select_related("author"), pk=pk)
    if not post.visible_to(request.user):
        raise PermissionDenied("You cannot access this post.")
    return post
