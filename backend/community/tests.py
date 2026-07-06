import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Follow
from .models import Post, PostLike

User = get_user_model()
STRONG_PW = "Sup3rSecret!pw"
POSTS = Path(tempfile.mkdtemp(prefix="gp-test-posts-"))
test_posts = override_settings(POSTS_ROOT=POSTS)

# 1x1 PNG.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000154a24f9f0000000049454e44ae426082"
)


def make_user(email, username, **kw):
    return User.objects.create_user(email=email, username=username, password=STRONG_PW, **kw)


def img(name="p.png"):
    return SimpleUploadedFile(name, PNG, content_type="image/png")


@test_posts
class PostTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(POSTS, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.a = make_user("a@t.com", "aa")
        self.b = make_user("b@t.com", "bb")
        self.client.force_authenticate(self.a)

    def test_create_text_post(self):
        res = self.client.post("/api/posts", {"body": "hello world"}, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["body"], "hello world")
        self.assertEqual(res.data["media"], [])

    def test_create_post_with_image(self):
        res = self.client.post("/api/posts", {"body": "pic", "media": img()}, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(len(res.data["media"]), 1)
        self.assertEqual(res.data["media"][0]["media_type"], "image")
        self.assertIn("?t=", res.data["media"][0]["url"])  # signed

    def test_empty_post_rejected(self):
        res = self.client.post("/api/posts", {"body": "  "}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_unsupported_media_rejected(self):
        bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/x-msdownload")
        res = self.client.post("/api/posts", {"media": bad}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Post.objects.count(), 0)  # rolled back

    def test_timeline_shows_followed_and_self(self):
        # b posts; a doesn't follow yet -> not in timeline.
        self.client.force_authenticate(self.b)
        self.client.post("/api/posts", {"body": "from b"}, format="multipart")
        self.client.force_authenticate(self.a)
        self.client.post("/api/posts", {"body": "from a"}, format="multipart")
        res = self.client.get("/api/posts")
        bodies = {p["body"] for p in res.data}
        self.assertIn("from a", bodies)
        self.assertNotIn("from b", bodies)
        # After following b, b's post appears.
        Follow.objects.create(follower=self.a, following=self.b)
        res = self.client.get("/api/posts")
        self.assertIn("from b", {p["body"] for p in res.data})

    def test_private_post_hidden_from_stranger(self):
        p = Post.objects.create(author=self.b, body="secret", visibility=Post.Visibility.PRIVATE)
        res = self.client.get(f"/api/posts/{p.id}")
        self.assertEqual(res.status_code, 403)

    def test_like_and_comment(self):
        p = Post.objects.create(author=self.a, body="x")
        r = self.client.post(f"/api/posts/{p.id}/like")
        self.assertEqual(r.data, {"liked": True, "likes_count": 1})
        self.assertTrue(PostLike.objects.filter(post=p, user=self.a).exists())
        r = self.client.post(f"/api/posts/{p.id}/comments", {"body": "nice"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["user"]["username"], "aa")

    def test_media_serve_requires_valid_token(self):
        res = self.client.post("/api/posts", {"media": img()}, format="multipart")
        url = res.data["media"][0]["url"]  # /media/posts/<id>/p.png?t=...
        # With the signed token -> served.
        ok = self.client.get(url)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(b"".join(ok.streaming_content)[:4], b"\x89PNG")
        # Without the token -> forbidden.
        no_token = url.split("?")[0]
        self.assertEqual(self.client.get(no_token).status_code, 403)
