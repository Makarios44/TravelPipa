"""
Restores photos and videos that the database points to but that are missing
from storage, using the originals kept in the project's ``content/`` folder.

Why: on Railway the container disk is wiped on every deploy. If MEDIA_ROOT is
not on a mounted Volume (or the Volume was attached late), the database keeps
pointing to files that no longer exist and the site shows broken images.
Running this on every start makes the site heal itself.

Files are restored byte for byte at the exact same path, so nothing in the
database changes. Photos the team uploaded through the panel have no copy in
``content/``; those are only reported.
"""
import logging
import re
from pathlib import Path

from django.conf import settings
from django.core.files import File

logger = logging.getLogger(__name__)

CONTENT_DIR = Path(settings.BASE_DIR) / "content"
# Django adds "_" + 7 random characters when a name is already taken.
DJANGO_SUFFIX = re.compile(r"_[A-Za-z0-9]{7}$")


def _content_index():
    index = {}
    if CONTENT_DIR.exists():
        for path in CONTENT_DIR.rglob("*"):
            if path.is_file():
                index.setdefault(path.stem.lower(), path)
    return index


def _find_source(name, index):
    stem = Path(name).stem
    for candidate in (stem, DJANGO_SUFFIX.sub("", stem)):
        source = index.get(candidate.lower())
        if source and source.suffix.lower() == Path(name).suffix.lower():
            return source
    return None


def _field_files():
    from core.models import SiteSettings
    from tours.models import Category, Experience, ExperienceImage

    for img in ExperienceImage.objects.all().only("id", "image"):
        yield img.image
    for exp in Experience.objects.all().only("id", "video", "video_poster"):
        yield exp.video
        yield exp.video_poster
    for cat in Category.objects.all().only("id", "image"):
        yield cat.image
    site = SiteSettings.objects.first()
    if site:
        for field in ("hero_image", "about_image", "logo", "og_image"):
            yield getattr(site, field)


def repair_missing_media():
    """Returns (restored, still_missing) lists of storage names."""
    index = _content_index()
    restored, missing = [], []
    for field_file in _field_files():
        name = getattr(field_file, "name", "")
        if not name:
            continue
        storage = field_file.storage
        try:
            if storage.exists(name):
                continue
        except Exception:  # pragma: no cover - storage hiccup: do not block the start
            logger.exception("Could not check media file %s", name)
            continue
        source = _find_source(name, index)
        if not source:
            missing.append(name)
            continue
        with source.open("rb") as fh:
            saved = storage.save(name, File(fh))
        if saved != name:  # pragma: no cover - only if the name was taken meanwhile
            logger.warning("Media %s restored as %s", name, saved)
        restored.append(name)
    return restored, missing
