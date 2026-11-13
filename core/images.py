"""
Image handling for uploads.

Quality first: an uploaded photo is kept exactly as sent (no re-encoding) unless
it is very large (longest side above settings.IMAGE_MAX_SIDE) or needs to be
rotated according to its EXIF orientation. Only then it is resized/rotated and
saved again at high quality.
"""
import logging
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
MAX_UPLOAD_MB = 15
JPEG_QUALITY = 92
EXIF_ORIENTATION = 0x0112


def validate_image_size(file):
    if file and file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationError(f"A imagem deve ter no máximo {MAX_UPLOAD_MB} MB.")


def optimize_image_field(field_file, max_side=None):
    """
    Resize the image in ``field_file`` only when its longest side is larger than
    ``max_side`` (or when it must be rotated). Otherwise the original file is kept
    untouched. Returns True when the file was rewritten.
    """
    if not field_file or getattr(field_file, "_committed", True) is True:
        # Only process freshly uploaded files (not yet committed to storage).
        return False
    max_side = max_side or settings.IMAGE_MAX_SIDE
    try:
        field_file.seek(0)
        img = Image.open(field_file)
        orientation = img.getexif().get(EXIF_ORIENTATION, 1)
        needs_resize = max(img.size) > max_side
        needs_rotation = orientation not in (None, 1)
        if not needs_resize and not needs_rotation:
            field_file.seek(0)
            return False  # keep the original bytes: no quality loss

        icc_profile = img.info.get("icc_profile")
        img = ImageOps.exif_transpose(img)
        if needs_resize:
            img.thumbnail((max_side, max_side), Image.LANCZOS)
        has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
        buffer = BytesIO()
        stem = Path(field_file.name).stem[:80]
        if has_alpha:
            img.save(buffer, format="PNG", optimize=True)
            name = f"{stem}.png"
        else:
            options = {"quality": JPEG_QUALITY, "subsampling": 0, "optimize": True, "progressive": True}
            if icc_profile:
                options["icc_profile"] = icc_profile  # keep the original colours
            img.convert("RGB").save(buffer, format="JPEG", **options)
            name = f"{stem}.jpg"
        field_file.save(name, ContentFile(buffer.getvalue()), save=False)
        return True
    except Exception:  # pragma: no cover - never block a save because of optimisation
        logger.exception("Could not optimise image %s", getattr(field_file, "name", ""))
        return False
