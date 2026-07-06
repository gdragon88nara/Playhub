"""Signed, access-controlled serving of DM attachments.

An <img> can't send an Authorization header, so the serializer — which only runs
for threads the viewer participates in — signs a short-lived token binding the
message id to the viewer. The serve view checks the token AND that the viewer is
still a participant, so DM files never leak via a bare URL."""

import mimetypes
import os

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404

DM_MEDIA_SALT = "chat.dm-attachment"


def signed_dm_url(message, viewer) -> str | None:
    if not message.attachment:
        return None
    token = signing.dumps({"m": message.id, "u": viewer.id}, salt=DM_MEDIA_SALT)
    return f"{settings.MEDIA_URL}dm/{message.id}/file?t={token}"


def serve_dm_media(request, message_id: int):
    from .models import DirectMessage

    token = request.GET.get("t", "")
    try:
        data = signing.loads(token, salt=DM_MEDIA_SALT, max_age=settings.PLAY_COOKIE_MAX_AGE)
        if data.get("m") != message_id:
            raise signing.BadSignature("message mismatch")
    except signing.BadSignature:
        return HttpResponseForbidden("Invalid or expired media link.")

    msg = get_object_or_404(DirectMessage.objects.select_related("thread"), pk=message_id)
    # The token is bound to a viewer; that viewer must still be in the thread.
    if data.get("u") not in (msg.thread.user_a_id, msg.thread.user_b_id):
        return HttpResponseForbidden("Not your thread.")
    if not msg.attachment:
        raise Http404("No attachment")

    full = os.path.abspath(msg.attachment.path)
    base = os.path.abspath(str(settings.DM_ROOT))
    if os.path.commonpath([base]) != os.path.commonpath([base, full]) or not os.path.isfile(full):
        raise Http404("Not found")

    ctype, _ = mimetypes.guess_type(full)
    resp = FileResponse(open(full, "rb"), content_type=ctype or "application/octet-stream")
    resp["Accept-Ranges"] = "bytes"
    return resp
