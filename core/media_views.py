"""
Serves uploaded media files (MEDIA_ROOT) when SERVE_MEDIA is on, e.g. on Railway
with a mounted volume.

Unlike django.views.static.serve, it supports HTTP Range requests, which Safari
on iPhone/iPad requires to play videos.
"""
import mimetypes
import os
import re

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotModified, StreamingHttpResponse
from django.utils._os import safe_join
from django.utils.http import http_date
from django.views.decorators.http import require_safe
from django.views.static import was_modified_since

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
CHUNK_SIZE = 64 * 1024


def _read_range(path, start, length):
    with open(path, "rb") as fh:
        fh.seek(start)
        remaining = length
        while remaining > 0:
            data = fh.read(min(CHUNK_SIZE, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


# Only photos and videos are ever uploaded; anything else is never served from
# the site's own domain (an HTML/SVG file there could run scripts as the site).
SERVABLE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".mp4", ".webm"}


@require_safe
def serve_media(request, path):
    if os.path.splitext(path)[1].lower() not in SERVABLE_EXTENSIONS:
        raise Http404
    try:
        full_path = safe_join(settings.MEDIA_ROOT, path)
    except (SuspiciousFileOperation, ValueError):
        raise Http404
    if not os.path.isfile(full_path):
        raise Http404

    stat = os.stat(full_path)
    if not was_modified_since(request.META.get("HTTP_IF_MODIFIED_SINCE"), stat.st_mtime):
        return HttpResponseNotModified()

    content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
    size = stat.st_size
    match = RANGE_RE.match(request.headers.get("Range", "").strip())

    if match and (match.group(1) or match.group(2)):
        first, last = match.groups()
        if first == "":  # suffix range: last N bytes
            length = min(int(last), size)
            start, end = size - length, size - 1
        else:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        if start >= size or start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        length = end - start + 1
        response = StreamingHttpResponse(_read_range(full_path, start, length), status=206,
                                         content_type=content_type)
        response["Content-Length"] = str(length)
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    else:
        response = FileResponse(open(full_path, "rb"), content_type=content_type)
        response["Content-Length"] = str(size)

    response["Accept-Ranges"] = "bytes"
    response["Last-Modified"] = http_date(stat.st_mtime)
    response["Cache-Control"] = "public, max-age=86400"
    return response
