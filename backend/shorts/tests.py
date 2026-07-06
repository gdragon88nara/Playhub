import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Short

User = get_user_model()
STRONG_PW = "Sup3rSecret!pw"
SHORTS = Path(tempfile.mkdtemp(prefix="gp-test-shorts-"))
test_shorts = override_settings(SHORTS_ROOT=SHORTS)


def make_user(email, username, **kw):
    return User.objects.create_user(email=email, username=username, password=STRONG_PW, **kw)


def video(name="clip.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42fakevideo", content_type="video/mp4")


@test_shorts
class ShortTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(SHORTS, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.a = make_user("a@t.com", "aa")
        self.b = make_user("b@t.com", "bb")
        self.client.force_authenticate(self.a)

    def test_upload_short(self):
        res = self.client.post("/api/shorts", {"caption": "my clip", "video": video()},
                               format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["caption"], "my clip")
        self.assertIn("?t=", res.data["video_url"])

    def test_non_video_rejected(self):
        bad = SimpleUploadedFile("x.txt", b"hello", content_type="text/plain")
        res = self.client.post("/api/shorts", {"video": bad}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Short.objects.count(), 0)

    def test_video_required(self):
        res = self.client.post("/api/shorts", {"caption": "no file"}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_feed_excludes_private_of_others(self):
        Short.objects.create(author=self.b, caption="secret",
                             visibility=Short.Visibility.PRIVATE, video=video())
        res = self.client.get("/api/shorts")
        self.assertEqual(len(res.data), 0)

    def test_like(self):
        s = Short.objects.create(author=self.a, video=video())
        r = self.client.post(f"/api/shorts/{s.id}/like")
        self.assertEqual(r.data, {"liked": True, "likes_count": 1})

    def test_serve_requires_token(self):
        res = self.client.post("/api/shorts", {"video": video()}, format="multipart")
        url = res.data["video_url"]  # /media/shorts/<id>/v?t=...
        ok = self.client.get(url)
        self.assertEqual(ok.status_code, 200)
        no_token = url.split("?")[0]
        self.assertEqual(self.client.get(no_token).status_code, 403)
