from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Block, Follow, FollowRequest, Report
from .serializers import (
    BlockSerializer,
    FollowRequestSerializer,
    MeSerializer,
    RegisterSerializer,
    ReportSerializer,
    UserPublicSerializer,
)

User = get_user_model()

# Refresh last_active at most this often to avoid a write on every request.
LAST_ACTIVE_THROTTLE = timedelta(minutes=5)


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register  — create account (optionally as seller)."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            MeSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/me — read or edit your own profile.

    A GET also refreshes ``last_active`` (throttled) — the client fetches /api/me
    on load and after actions, so this is a good "last seen" signal."""

    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        now = timezone.now()
        if user.last_active is None or now - user.last_active > LAST_ACTIVE_THROTTLE:
            user.last_active = now
            user.save(update_fields=["last_active"])
        return super().retrieve(request, *args, **kwargs)


class UserDetailView(generics.RetrieveAPIView):
    """GET /api/users/<username> — public profile by handle."""

    serializer_class = UserPublicSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "username"
    queryset = User.objects.all()


class FollowView(APIView):
    """POST/DELETE /api/users/<username>/follow.

    * Public target  -> immediate follow.
    * Private target -> creates a pending FollowRequest (unless already
      following). Acceptance (see FollowRequestActionView) auto-creates the
      mutual reverse edge.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        target = get_object_or_404(User, username=username)
        if target == request.user:
            return Response({"detail": "Cannot follow yourself."},
                            status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_following(target):
            return Response({"status": "following"})

        if target.is_private:
            fr, _ = FollowRequest.objects.get_or_create(
                requester=request.user, target=target,
                status=FollowRequest.Status.PENDING,
            )
            return Response({"status": "requested", "request_id": fr.id},
                            status=status.HTTP_202_ACCEPTED)

        Follow.objects.get_or_create(follower=request.user, following=target)
        return Response({"status": "following"}, status=status.HTTP_201_CREATED)

    def delete(self, request, username):
        target = get_object_or_404(User, username=username)
        Follow.objects.filter(follower=request.user, following=target).delete()
        FollowRequest.objects.filter(
            requester=request.user, target=target,
            status=FollowRequest.Status.PENDING,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IncomingFollowRequestsView(generics.ListAPIView):
    """GET /api/follow-requests — pending requests addressed to me."""

    serializer_class = FollowRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            FollowRequest.objects.filter(
                target=self.request.user, status=FollowRequest.Status.PENDING
            )
            .select_related("requester")
            .order_by("-created_at")
        )


class FollowRequestActionView(APIView):
    """POST /api/follow-requests/<id>/<accept|reject>."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        fr = get_object_or_404(
            FollowRequest, pk=pk, target=request.user,
            status=FollowRequest.Status.PENDING,
        )
        if action == "accept":
            fr.accept()
            return Response({"status": "accepted"})
        if action == "reject":
            fr.reject()
            return Response({"status": "rejected"})
        return Response({"detail": "Unknown action."},
                        status=status.HTTP_400_BAD_REQUEST)


class FollowListView(generics.ListAPIView):
    """GET /api/users/<username>/<followers|following>.

    Respects privacy: a private account's follow lists are only visible to the
    owner and to accepted followers.
    """

    serializer_class = UserPublicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        target = get_object_or_404(User, username=self.kwargs["username"])
        if not target.can_view_content(self.request.user):
            return User.objects.none()
        which = self.kwargs["which"]
        if which == "followers":
            return User.objects.filter(following_edges__following=target)
        return User.objects.filter(follower_edges__follower=target)


# ---------------------------------------------------------------------------
# "Menu" endpoints — the account/activity hub behind the hamburger menu.
# Aggregations import games/community models lazily to avoid import cycles.
# ---------------------------------------------------------------------------
class MyActivityView(APIView):
    """GET /api/me/activity — counts summarising my footprint on the platform."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user
        from games.models import Comment, Game, Like
        from community.models import Post, PostComment, PostLike

        return Response({
            "games": Game.objects.filter(owner=me).count(),
            "posts": Post.objects.filter(author=me).count(),
            "comments": (Comment.objects.filter(user=me).count()
                         + PostComment.objects.filter(user=me).count()),
            "likes_given": (Like.objects.filter(user=me).count()
                            + PostLike.objects.filter(user=me).count()),
            "likes_received": (Like.objects.filter(game__owner=me).count()
                               + PostLike.objects.filter(post__author=me).count()),
            "followers": me.followers_count,
            "following": me.following_count,
            "member_since": me.date_joined,
            "last_active": me.last_active,
        })


class NotificationsView(APIView):
    """GET /api/me/notifications — an aggregated activity feed (follow requests,
    new followers, likes, comments on my content). Honours my notify_* prefs and
    hides anyone I've blocked."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user
        from games.models import Comment, Like
        from community.models import PostComment, PostLike

        blocked = set(Block.objects.filter(blocker=me).values_list("blocked_id", flat=True))
        items = []

        for fr in (FollowRequest.objects
                   .filter(target=me, status=FollowRequest.Status.PENDING)
                   .select_related("requester")[:50]):
            if fr.requester_id in blocked:
                continue
            items.append(_notif("follow_request", fr.id, fr.requester,
                                 "requested to follow you", fr.created_at))

        if me.notify_follows:
            for f in (Follow.objects.filter(following=me)
                      .select_related("follower").order_by("-created_at")[:30]):
                if f.follower_id in blocked:
                    continue
                items.append(_notif("follow", f.id, f.follower,
                                    "started following you", f.created_at))

        if me.notify_likes:
            for lk in (Like.objects.filter(game__owner=me).exclude(user=me)
                       .select_related("user", "game").order_by("-created_at")[:30]):
                if lk.user_id in blocked:
                    continue
                items.append(_notif("like", f"g{lk.id}", lk.user,
                                    f"liked your game “{lk.game.title}”", lk.created_at,
                                    url=f"/games/{lk.game.slug}"))
            for pl in (PostLike.objects.filter(post__author=me).exclude(user=me)
                       .select_related("user").order_by("-created_at")[:30]):
                if pl.user_id in blocked:
                    continue
                items.append(_notif("like", f"p{pl.id}", pl.user,
                                    "liked your post", pl.created_at,
                                    url=f"/community/{pl.post_id}"))

        if me.notify_comments:
            for c in (Comment.objects.filter(game__owner=me).exclude(user=me)
                      .select_related("user", "game").order_by("-created_at")[:30]):
                if c.user_id in blocked:
                    continue
                items.append(_notif("comment", f"g{c.id}", c.user,
                                    f"commented on “{c.game.title}”", c.created_at,
                                    url=f"/games/{c.game.slug}"))
            for c in (PostComment.objects.filter(post__author=me).exclude(user=me)
                      .select_related("user").order_by("-created_at")[:30]):
                if c.user_id in blocked:
                    continue
                items.append(_notif("comment", f"p{c.id}", c.user,
                                    "commented on your post", c.created_at,
                                    url=f"/community/{c.post_id}"))

        items.sort(key=lambda it: it["created_at"], reverse=True)
        return Response(items[:60])


def _notif(kind, pk, actor, text, created_at, url=None):
    return {
        "id": f"{kind}:{pk}",
        "type": kind,
        "actor": {"username": actor.username, "display_name": actor.display_name},
        "text": text,
        "url": url or f"/u/{actor.username}",
        "created_at": created_at,
    }


class MyCommentsView(APIView):
    """GET /api/me/comments — every comment I've written (games + posts)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user
        from games.models import Comment
        from community.models import PostComment

        items = []
        for c in (Comment.objects.filter(user=me)
                  .select_related("game").order_by("-created_at")[:100]):
            items.append({
                "id": f"g{c.id}", "kind": "game", "body": c.body,
                "target": c.game.title, "url": f"/games/{c.game.slug}",
                "created_at": c.created_at,
            })
        for c in (PostComment.objects.filter(user=me)
                  .select_related("post").order_by("-created_at")[:100]):
            items.append({
                "id": f"p{c.id}", "kind": "post", "body": c.body,
                "target": "Post", "url": f"/community/{c.post_id}",
                "created_at": c.created_at,
            })
        items.sort(key=lambda it: it["created_at"], reverse=True)
        return Response(items[:150])


class MyFavoritesView(APIView):
    """GET /api/me/favorites — games and posts I've liked (my favorites)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user
        from games.models import Like
        from games.serializers import GameListSerializer
        from community.models import PostLike
        from community.serializers import PostSerializer

        ctx = {"request": request}
        games = [
            GameListSerializer(lk.game, context=ctx).data
            for lk in Like.objects.filter(user=me)
            .select_related("game", "game__owner").order_by("-created_at")
        ]
        posts = [
            PostSerializer(pl.post, context=ctx).data
            for pl in PostLike.objects.filter(user=me)
            .select_related("post", "post__author").order_by("-created_at")
            if pl.post.visible_to(me)
        ]
        return Response({"games": games, "posts": posts})


class BlockListView(generics.ListAPIView):
    """GET /api/blocks — accounts I've blocked."""

    serializer_class = BlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Block.objects.filter(blocker=self.request.user).select_related("blocked")


class BlockView(APIView):
    """POST/DELETE /api/blocks/<username> — block or unblock a user. Blocking also
    tears down any follow relationship in both directions."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, username):
        target = get_object_or_404(User, username=username)
        if target == request.user:
            return Response({"detail": "You cannot block yourself."},
                            status=status.HTTP_400_BAD_REQUEST)
        Block.objects.get_or_create(blocker=request.user, blocked=target)
        Follow.objects.filter(follower=request.user, following=target).delete()
        Follow.objects.filter(follower=target, following=request.user).delete()
        FollowRequest.objects.filter(requester=request.user, target=target,
                                     status=FollowRequest.Status.PENDING).delete()
        FollowRequest.objects.filter(requester=target, target=request.user,
                                     status=FollowRequest.Status.PENDING).delete()
        return Response({"blocked": True}, status=status.HTTP_201_CREATED)

    def delete(self, request, username):
        target = get_object_or_404(User, username=username)
        Block.objects.filter(blocker=request.user, blocked=target).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportCreateView(generics.CreateAPIView):
    """POST /api/reports — submit an abuse/safety report."""

    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class SearchView(APIView):
    """GET /api/search?q=<term>&type=all|users|games|posts

    Unified search over users (handle/name), games (title/description) and posts
    (body). Everything respects visibility: only games/posts the viewer may see
    are returned, and blocked accounts are hidden."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q

        me = request.user
        q = (request.query_params.get("q") or "").strip()
        want = request.query_params.get("type", "all")
        ctx = {"request": request}
        result = {"users": [], "games": [], "posts": []}
        if not q:
            return Response(result)

        if want in ("all", "users"):
            blocked = set(Block.objects.filter(blocker=me).values_list("blocked_id", flat=True))
            blocked |= set(Block.objects.filter(blocked=me).values_list("blocker_id", flat=True))
            users = (
                User.objects.filter(Q(username__icontains=q) | Q(display_name__icontains=q))
                .exclude(id__in=blocked)
                .order_by("username")[:20]
            )
            result["users"] = UserPublicSerializer(users, many=True, context=ctx).data

        if want in ("all", "games"):
            from games.serializers import GameListSerializer
            from games.views import visible_games_qs
            games = visible_games_qs(me).filter(
                Q(title__icontains=q) | Q(description__icontains=q)
            )[:20]
            result["games"] = GameListSerializer(games, many=True, context=ctx).data

        if want in ("all", "posts"):
            from community.models import Post
            from community.serializers import PostSerializer
            candidates = (
                Post.objects.filter(body__icontains=q)
                .select_related("author").prefetch_related("media", "likes")
                .order_by("-created_at")[:100]
            )
            visible = [p for p in candidates if p.visible_to(me)][:20]
            result["posts"] = PostSerializer(visible, many=True, context=ctx).data

        return Response(result)
