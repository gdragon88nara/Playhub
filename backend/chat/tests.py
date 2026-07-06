from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application
from .models import ChatRoom, DirectMessage, DirectThread

User = get_user_model()
STRONG_PW = "Sup3rSecret!pw"


def make_user(email, username):
    return User.objects.create_user(email=email, username=username, password=STRONG_PW)


def token_for(user):
    return str(AccessToken.for_user(user))


async def connect(path):
    comm = WebsocketCommunicator(application, path)
    connected, _ = await comm.connect()
    return comm, connected


class DMConsumerTests(TransactionTestCase):
    def setUp(self):
        self.a = make_user("a@t.com", "aa")
        self.b = make_user("b@t.com", "bb")
        self.c = make_user("c@t.com", "cc")
        self.thread, _ = DirectThread.get_or_create_between(self.a, self.b)

    def test_realtime_delivery_and_persistence(self):
        async def scenario():
            ca, ok_a = await connect(f"/ws/dm/{self.thread.id}/?token={token_for(self.a)}")
            cb, ok_b = await connect(f"/ws/dm/{self.thread.id}/?token={token_for(self.b)}")
            self.assertTrue(ok_a)
            self.assertTrue(ok_b)

            await ca.send_json_to({"body": "hi bob"})
            got = await cb.receive_json_from(timeout=5)
            self.assertEqual(got["body"], "hi bob")
            self.assertEqual(got["sender"], "aa")

            await ca.disconnect()
            await cb.disconnect()

        async_to_sync(scenario)()
        # Message was persisted.
        self.assertEqual(DirectMessage.objects.filter(thread=self.thread).count(), 1)

    def test_non_participant_rejected(self):
        async def scenario():
            cc, ok = await connect(f"/ws/dm/{self.thread.id}/?token={token_for(self.c)}")
            self.assertFalse(ok)  # closed before accept
            await cc.disconnect()

        async_to_sync(scenario)()

    def test_unauthenticated_rejected(self):
        async def scenario():
            comm, ok = await connect(f"/ws/dm/{self.thread.id}/")
            self.assertFalse(ok)
            await comm.disconnect()

        async_to_sync(scenario)()


import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

DM = Path(tempfile.mkdtemp(prefix="gp-test-dm-"))


@override_settings(DM_ROOT=DM)
class DMAttachmentTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DM, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.a = make_user("a2@t.com", "a2")
        self.b = make_user("b2@t.com", "b2")
        self.c = make_user("c2@t.com", "c2")
        self.thread, _ = DirectThread.get_or_create_between(self.a, self.b)

    def test_send_attachment_and_list_and_serve(self):
        self.client.force_authenticate(self.a)
        img = SimpleUploadedFile("pic.png", b"\x89PNG\r\n\x1a\nfake", content_type="image/png")
        res = self.client.post(f"/api/dm/threads/{self.thread.id}/attachments", {"file": img}, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["attachment_type"], "image")
        self.assertTrue(res.data["attachment_url"])

        # Recipient sees it in their DM media hub.
        self.client.force_authenticate(self.b)
        media = self.client.get("/api/dm/media")
        self.assertEqual(media.status_code, 200)
        self.assertEqual(len(media.data), 1)
        url = media.data[0]["url"]
        # The signed URL serves the bytes to a participant.
        served = self.client.get(url)
        self.assertEqual(served.status_code, 200)

    def test_non_participant_cannot_post_attachment(self):
        self.client.force_authenticate(self.c)
        img = SimpleUploadedFile("x.png", b"data", content_type="image/png")
        res = self.client.post(f"/api/dm/threads/{self.thread.id}/attachments", {"file": img}, format="multipart")
        self.assertEqual(res.status_code, 403)


class RoomConsumerTests(TransactionTestCase):
    def setUp(self):
        self.u = make_user("u@t.com", "uu")
        self.room = ChatRoom.objects.create(slug="lobby", name="Lobby")

    def test_open_room_broadcast(self):
        async def scenario():
            c1, ok1 = await connect(f"/ws/room/lobby/?token={token_for(self.u)}")
            self.assertTrue(ok1)
            await c1.send_json_to({"body": "hello room"})
            got = await c1.receive_json_from(timeout=5)
            self.assertEqual(got["body"], "hello room")
            self.assertEqual(got["sender"], "uu")
            await c1.disconnect()

        async_to_sync(scenario)()
