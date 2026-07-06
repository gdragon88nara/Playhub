"""Signed, access-controlled serving of post media (images/videos).

Feed images/videos are leaf resources loaded by <img>/<video> tags that cannot
send an Authorization header. Instead the serializer — which only ever runs for
posts the viewer is allowed to see — appends a short-lived signed token to each
media URL. The serve view validates that token, so private/followers media is
never reachable by a bare URL."""

import mimetypes
import os

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404

MEDIA_SALT = "community.post-media"


def signed_media_url(media) -> str:
    token = signing.dumps({"p": media.post_id}, salt=MEDIA_SALT)
    filename = os.path.basename(media.file.name)
    return f"{settings.MEDIA_URL}posts/{media.post_id}/{filename}?t={token}"


def serve_post_media(request, post_id: int, filename: str):
    token = request.GET.get("t", "")
    try:
        data = signing.loads(token, salt=MEDIA_SALT, max_age=settings.PLAY_COOKIE_MAX_AGE)
        if data.get("p") != post_id:
            raise signing.BadSignature("post mismatch")
    except signing.BadSignature:
        return HttpResponseForbidden("Invalid or expired media link.")

    base = os.path.abspath(os.path.join(settings.POSTS_ROOT, str(post_id)))
    full = os.path.abspath(os.path.join(base, filename))
    if os.path.commonpath([base]) != os.path.commonpath([base, full]) or not os.path.isfile(full):
        raise Http404("Not found")

    ctype, _ = mimetypes.guess_type(full)
    resp = FileResponse(open(full, "rb"), content_type=ctype or "application/octet-stream")
    resp["Accept-Ranges"] = "bytes"
    return resp
