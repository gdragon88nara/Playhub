import io
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Follow
from .models import Game, SavedGame

User = get_user_model()
STRONG_PW = "Sup3rSecret!pw"
MEDIA = tempfile.mkdtemp(prefix="gp-test-media-")
GAMES = Path(tempfile.mkdtemp(prefix="gp-test-games-"))
test_media = override_settings(MEDIA_ROOT=MEDIA, GAMES_ROOT=GAMES)


def make_user(email, username, **kw):
    return User.objects.create_user(email=email, username=username, password=STRONG_PW, **kw)


def make_zip(files=None, root=None):
    """Build an in-memory ZIP. ``root`` wraps files in a single top dir."""
    files = files or {"index.html": "<h1>Hello game</h1>"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            arc = f"{root}/{name}" if root else name
            zf.writestr(arc, content)
    buf.seek(0)
    buf.name = "game.zip"
    return buf


@test_media
class GameUploadTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.dev = make_user("dev@t.com", "dev")
        self.client.force_authenticate(self.dev)

    def test_upload_deploys_immediately(self):
        res = self.client.post("/api/games", {
            "title": "My Game", "engine": "html", "bundle": make_zip(),
        }, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["status"], "deployed")
        self.assertEqual(res.data["entry_file"], "index.html")
        self.assertTrue(res.data["play_url"].endswith("/index.html"))

    def test_single_root_dir_is_hoisted(self):
        # Unity exports often wrap everything in a folder.
        res = self.client.post("/api/games", {
            "title": "Unity Game", "engine": "unity_webgl",
            "bundle": make_zip(root="UnityBuild"),
        }, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["entry_file"], "index.html")

    def test_zip_without_index_rejected(self):
        res = self.client.post("/api/games", {
            "title": "Bad", "bundle": make_zip({"main.js": "x"}),
        }, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Game.objects.filter(title="Bad").exists())  # rolled back

    def test_zip_slip_rejected(self):
        res = self.client.post("/api/games", {
            "title": "Evil", "bundle": make_zip({"../evil.html": "x", "index.html": "ok"}),
        }, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_paid_game_requires_price(self):
        res = self.client.post("/api/games", {
            "title": "Paid", "is_paid": True, "price": 0, "bundle": make_zip(),
        }, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_upload_direct_files_deploys(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        res = self.client.post("/api/games", {
            "title": "Direct", "engine": "html",
            "files": [
                SimpleUploadedFile("index.html", b"<h1>Hi</h1>"),
                SimpleUploadedFile("main.js", b"console.log(1)"),
            ],
            "paths": ["MyGame/index.html", "MyGame/main.js"],
        }, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["status"], "deployed")
        # The wrapping folder is hoisted so index.html sits at the root.
        self.assertEqual(res.data["entry_file"], "index.html")

    def test_upload_with_genre_and_thumbnail(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (2, 2), (99, 102, 241)).save(buf, "PNG")
        thumb = SimpleUploadedFile("t.png", buf.getvalue(), content_type="image/png")
        res = self.client.post("/api/games", {
            "title": "Genred", "engine": "unity_webgl", "genre": "rpg",
            "bundle": make_zip(), "thumbnail": thumb,
        }, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["genre"], "rpg")
        self.assertTrue(res.data["thumbnail"])

    def test_list_filter_by_genre(self):
        self.client.post("/api/games", {"title": "Puz", "genre": "puzzle", "bundle": make_zip()}, format="multipart")
        self.client.post("/api/games", {"title": "Act", "genre": "action", "bundle": make_zip()}, format="multipart")
        res = self.client.get("/api/games?genre=puzzle")
        titles = {g["title"] for g in res.data}
        self.assertIn("Puz", titles)
        self.assertNotIn("Act", titles)

    def test_upload_direct_files_without_index_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        res = self.client.post("/api/games", {
            "title": "NoIndex",
            "files": [SimpleUploadedFile("main.js", b"x")],
            "paths": ["main.js"],
        }, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Game.objects.filter(title="NoIndex").exists())  # rolled back


@test_media
class GameVisibilityTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.owner = make_user("o@t.com", "owner")
        self.follower = make_user("f@t.com", "follower")
        self.stranger = make_user("s@t.com", "stranger")

    def deploy(self, title="G", **kw):
        g = Game(owner=self.owner, title=title, status=Game.Status.DEPLOYED,
                 entry_file="index.html", **kw)
        g.save()
        return g

    def test_public_game_visible_to_all(self):
        g = self.deploy(visibility=Game.Visibility.PUBLIC)
        self.client.force_authenticate(self.stranger)
        res = self.client.get(f"/api/games/{g.slug}")
        self.assertEqual(res.status_code, 200)

    def test_followers_only_hidden_from_stranger(self):
        g = self.deploy(visibility=Game.Visibility.FOLLOWERS)
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.get(f"/api/games/{g.slug}").status_code, 403)
        # Follower can see it.
        Follow.objects.create(follower=self.follower, following=self.owner)
        self.client.force_authenticate(self.follower)
        self.assertEqual(self.client.get(f"/api/games/{g.slug}").status_code, 200)

    def test_private_game_owner_only(self):
        g = self.deploy(visibility=Game.Visibility.PRIVATE)
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.get(f"/api/games/{g.slug}").status_code, 403)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(f"/api/games/{g.slug}").status_code, 200)

    def test_feed_excludes_hidden_games(self):
        self.deploy(visibility=Game.Visibility.PUBLIC, title="pub")
        self.deploy(visibility=Game.Visibility.PRIVATE, title="priv")
        self.client.force_authenticate(self.stranger)
        res = self.client.get("/api/games")
        titles = {g["title"] for g in res.data}
        self.assertIn("pub", titles)
        self.assertNotIn("priv", titles)


@test_media
class GameInteractionTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.owner = make_user("o2@t.com", "owner2")
        self.user = make_user("u@t.com", "player")
        self.game = Game(owner=self.owner, title="Play", status=Game.Status.DEPLOYED,
                         entry_file="index.html", visibility=Game.Visibility.PUBLIC)
        self.game.save()
        self.client.force_authenticate(self.user)

    def test_like_and_unlike(self):
        r = self.client.post(f"/api/games/{self.game.slug}/like")
        self.assertEqual(r.data, {"liked": True, "likes_count": 1})
        r = self.client.delete(f"/api/games/{self.game.slug}/like")
        self.assertEqual(r.data, {"liked": False, "likes_count": 0})

    def test_save_and_library(self):
        self.client.post(f"/api/games/{self.game.slug}/save")
        self.assertTrue(SavedGame.objects.filter(user=self.user, game=self.game).exists())
        res = self.client.get("/api/me/saved")
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["game"]["title"], "Play")

    def test_comment(self):
        r = self.client.post(f"/api/games/{self.game.slug}/comments",
                             {"body": "nice game"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["user"]["username"], "player")
        r = self.client.get(f"/api/games/{self.game.slug}/comments")
        self.assertEqual(len(r.data), 1)

    def test_play_increments_count(self):
        r = self.client.post(f"/api/games/{self.game.slug}/play")
        self.assertEqual(r.status_code, 200)
        self.game.refresh_from_db()
        self.assertEqual(self.game.play_count, 1)


@test_media
class GameServeTests(APITestCase):
    """The bundle is served only via the authenticated Python view, never as a
    public file, and only inside the site."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        shutil.rmtree(GAMES, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.dev = make_user("srv@t.com", "srv")
        self.client.force_authenticate(self.dev)
        res = self.client.post("/api/games", {
            "title": "Served", "engine": "html",
            "bundle": make_zip({"index.html": "<h1>PLAYABLE</h1>"}),
        }, format="multipart")
        self.game_id = res.data["id"]
        self.url = f"/media/games/{self.game_id}/index.html"

    def test_serve_denied_without_play_cookie(self):
        self.client.cookies.clear()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 403)

    def test_serve_allowed_after_play(self):
        slug = Game.objects.get(pk=self.game_id).slug
        play = self.client.post(f"/api/games/{slug}/play")
        self.assertEqual(play.status_code, 200)
        # The play response set the signed access cookie; the client resends it.
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        body = b"".join(res.streaming_content)
        self.assertIn(b"PLAYABLE", body)
        # In-site-only embed policy is attached.
        self.assertIn("frame-ancestors", res["Content-Security-Policy"])

    def test_path_traversal_on_serve_blocked(self):
        slug = Game.objects.get(pk=self.game_id).slug
        self.client.post(f"/api/games/{slug}/play")
        res = self.client.get(f"/media/games/{self.game_id}/../../secret.txt")
        self.assertIn(res.status_code, (403, 404))
