from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Block, Follow, FollowRequest, Report, SellerProfile

User = get_user_model()

STRONG_PW = "Sup3rSecret!pw"


def make_user(email, username, **kw):
    return User.objects.create_user(email=email, username=username, password=STRONG_PW, **kw)


class MenuEndpointTests(APITestCase):
    """The account-menu hub: activity, notifications, comments, favorites, safety."""

    def setUp(self):
        self.me = make_user("me@t.com", "me")
        self.other = make_user("o@t.com", "other")
        self.client.force_authenticate(self.me)

    def test_me_exposes_prefs_and_updates_last_active(self):
        res = self.client.get("/api/me")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["notify_likes"])
        self.assertIsNotNone(res.data["last_active"])

    def test_update_notification_prefs_and_privacy(self):
        res = self.client.patch("/api/me", {"notify_likes": False, "is_private": True}, format="json")
        self.assertEqual(res.status_code, 200)
        self.me.refresh_from_db()
        self.assertFalse(self.me.notify_likes)
        self.assertTrue(self.me.is_private)

    def test_activity_summary(self):
        res = self.client.get("/api/me/activity")
        self.assertEqual(res.status_code, 200)
        for key in ("games", "posts", "comments", "likes_given", "followers"):
            self.assertIn(key, res.data)

    def test_notifications_include_follow_request(self):
        priv = make_user("p@t.com", "priv", is_private=True)
        self.client.force_authenticate(self.other)
        self.client.post("/api/users/priv/follow")  # creates a pending request
        self.client.force_authenticate(priv)
        res = self.client.get("/api/me/notifications")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any(n["type"] == "follow_request" for n in res.data))

    def test_notifications_include_like_on_my_game(self):
        from games.models import Game, Like
        g = Game.objects.create(owner=self.me, title="G", status=Game.Status.DEPLOYED,
                                entry_file="index.html")
        Like.objects.create(user=self.other, game=g)
        res = self.client.get("/api/me/notifications")
        self.assertTrue(any(n["type"] == "like" for n in res.data))
        # Disabling the like preference hides them.
        self.client.patch("/api/me", {"notify_likes": False}, format="json")
        res2 = self.client.get("/api/me/notifications")
        self.assertFalse(any(n["type"] == "like" for n in res2.data))

    def test_favorites_reflect_liked_game(self):
        from games.models import Game, Like
        g = Game.objects.create(owner=self.other, title="Fav", status=Game.Status.DEPLOYED,
                                entry_file="index.html", visibility=Game.Visibility.PUBLIC)
        Like.objects.create(user=self.me, game=g)
        res = self.client.get("/api/me/favorites")
        self.assertEqual(len(res.data["games"]), 1)
        self.assertEqual(res.data["games"][0]["title"], "Fav")

    def test_favorites_and_comments_empty_ok(self):
        fav = self.client.get("/api/me/favorites")
        self.assertEqual(fav.status_code, 200)
        self.assertEqual(fav.data, {"games": [], "posts": []})
        com = self.client.get("/api/me/comments")
        self.assertEqual(com.status_code, 200)
        self.assertEqual(com.data, [])

    def test_block_unblock_and_teardown_follow(self):
        Follow.objects.create(follower=self.me, following=self.other)
        Follow.objects.create(follower=self.other, following=self.me)
        res = self.client.post("/api/blocks/other")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Block.objects.filter(blocker=self.me, blocked=self.other).exists())
        # Blocking removes the follow relationship both ways.
        self.assertFalse(Follow.objects.filter(follower=self.me, following=self.other).exists())
        self.assertFalse(Follow.objects.filter(follower=self.other, following=self.me).exists())
        lst = self.client.get("/api/blocks")
        self.assertEqual(len(lst.data), 1)
        self.client.delete("/api/blocks/other")
        self.assertFalse(Block.objects.filter(blocker=self.me).exists())

    def test_search_across_users_games_posts(self):
        from games.models import Game
        from community.models import Post
        Game.objects.create(owner=self.other, title="Space Runner", status=Game.Status.DEPLOYED,
                            entry_file="index.html", visibility=Game.Visibility.PUBLIC)
        Post.objects.create(author=self.other, body="my space adventure", visibility=Post.Visibility.PUBLIC)
        res = self.client.get("/api/search?q=space")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any(g["title"] == "Space Runner" for g in res.data["games"]))
        self.assertTrue(any("space" in p["body"] for p in res.data["posts"]))
        ru = self.client.get("/api/search?q=other")
        self.assertTrue(any(u["username"] == "other" for u in ru.data["users"]))

    def test_search_hides_blocked_user(self):
        Block.objects.create(blocker=self.me, blocked=self.other)
        res = self.client.get("/api/search?q=other")
        self.assertFalse(any(u["username"] == "other" for u in res.data["users"]))

    def test_search_hides_private_game_of_others(self):
        from games.models import Game
        Game.objects.create(owner=self.other, title="Secret Space", status=Game.Status.DEPLOYED,
                            entry_file="index.html", visibility=Game.Visibility.PRIVATE)
        res = self.client.get("/api/search?q=secret")
        self.assertFalse(any(g["title"] == "Secret Space" for g in res.data["games"]))

    def test_search_empty_query_returns_empty(self):
        res = self.client.get("/api/search?q=")
        self.assertEqual(res.data, {"users": [], "games": [], "posts": []})

    def test_cannot_block_self(self):
        self.assertEqual(self.client.post("/api/blocks/me").status_code, 400)

    def test_create_report(self):
        res = self.client.post("/api/reports", {
            "kind": "user", "target": "other", "reason": "spam", "note": "bot",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(Report.objects.filter(reporter=self.me, target="other").exists())


class RegistrationTests(APITestCase):
    def test_register_normal_user(self):
        res = self.client.post("/api/auth/register", {
            "email": "A@Example.com", "username": "alice",
            "password": STRONG_PW, "display_name": "Alice",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        # Email is normalised to lowercase.
        self.assertEqual(res.data["email"], "a@example.com")
        self.assertFalse(res.data["is_seller"])

    def test_register_seller_creates_profile(self):
        res = self.client.post("/api/auth/register", {
            "email": "s@example.com", "username": "seller1",
            "password": STRONG_PW, "become_seller": True,
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["is_seller"])
        user = User.objects.get(username="seller1")
        self.assertTrue(SellerProfile.objects.filter(user=user).exists())

    def test_weak_password_rejected(self):
        res = self.client.post("/api/auth/register", {
            "email": "w@example.com", "username": "weak", "password": "123",
        }, format="json")
        self.assertEqual(res.status_code, 400)


class AuthTests(APITestCase):
    def test_login_returns_jwt(self):
        make_user("l@example.com", "loginuser")
        res = self.client.post("/api/auth/login", {
            "email": "l@example.com", "password": STRONG_PW,
        }, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)


class FollowTests(APITestCase):
    def setUp(self):
        self.alice = make_user("alice@example.com", "alice")
        self.bob = make_user("bob@example.com", "bob")  # public
        self.carol = make_user("carol@example.com", "carol", is_private=True)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_follow_public_is_immediate(self):
        self.auth(self.alice)
        res = self.client.post(f"/api/users/{self.bob.username}/follow")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["status"], "following")
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())
        # Not automatically mutual for public follows.
        self.assertFalse(Follow.objects.filter(follower=self.bob, following=self.alice).exists())

    def test_follow_private_creates_request(self):
        self.auth(self.alice)
        res = self.client.post(f"/api/users/{self.carol.username}/follow")
        self.assertEqual(res.status_code, 202, res.data)
        self.assertEqual(res.data["status"], "requested")
        self.assertFalse(Follow.objects.filter(follower=self.alice, following=self.carol).exists())
        self.assertTrue(FollowRequest.objects.filter(
            requester=self.alice, target=self.carol, status="pending").exists())

    def test_accept_request_creates_mutual_follow(self):
        # Alice requests to follow private Carol.
        self.auth(self.alice)
        self.client.post(f"/api/users/{self.carol.username}/follow")
        fr = FollowRequest.objects.get(requester=self.alice, target=self.carol)
        # Carol accepts.
        self.auth(self.carol)
        res = self.client.post(f"/api/follow-requests/{fr.id}/accept")
        self.assertEqual(res.status_code, 200, res.data)
        # Both directions now exist (auto mutual follow).
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.carol).exists())
        self.assertTrue(Follow.objects.filter(follower=self.carol, following=self.alice).exists())
        fr.refresh_from_db()
        self.assertEqual(fr.status, "accepted")

    def test_follow_status_transitions(self):
        self.client.force_authenticate(self.alice)
        # none -> request a private account -> requested
        self.assertEqual(self.client.get("/api/users/carol").data["follow_status"], "none")
        self.client.post("/api/users/carol/follow")
        self.assertEqual(self.client.get("/api/users/carol").data["follow_status"], "requested")
        # own profile -> self
        self.assertEqual(self.client.get("/api/users/alice").data["follow_status"], "self")
        # follow a public account -> following
        self.client.post("/api/users/bob/follow")
        self.assertEqual(self.client.get("/api/users/bob").data["follow_status"], "following")

    def test_reject_request_no_follow(self):
        self.auth(self.alice)
        self.client.post(f"/api/users/{self.carol.username}/follow")
        fr = FollowRequest.objects.get(requester=self.alice, target=self.carol)
        self.auth(self.carol)
        res = self.client.post(f"/api/follow-requests/{fr.id}/reject")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Follow.objects.filter(follower=self.alice, following=self.carol).exists())

    def test_unfollow(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.auth(self.alice)
        res = self.client.delete(f"/api/users/{self.bob.username}/follow")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Follow.objects.filter(follower=self.alice, following=self.bob).exists())

    def test_private_followers_list_hidden_from_stranger(self):
        # Carol is private; Alice is not a follower -> cannot see her lists.
        self.auth(self.alice)
        res = self.client.get(f"/api/users/{self.carol.username}/followers")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 0)
