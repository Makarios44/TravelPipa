"""
Generates clearly labelled *demo* images (stylised coastal illustrations) so the
site can be previewed before real photographs of Pipa are uploaded.
Every image carries a visible "DEMO IMAGE" label.
"""
import math
import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OCEAN = (18, 59, 80)
TEAL = (0, 127, 134)
SUN = (255, 181, 71)
CORAL = (244, 119, 69)
SAND = (255, 248, 239)
CLIFF = (196, 106, 62)
CLIFF_LIGHT = (226, 150, 92)
FOREST = (46, 104, 78)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _vertical_gradient(draw, box, top, bottom):
    x0, y0, x1, y1 = box
    h = max(1, y1 - y0)
    for y in range(y0, y1):
        draw.line([(x0, y), (x1, y)], fill=_lerp(top, bottom, (y - y0) / h))


def _font(size):
    for name in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _label(img, text):
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    size = max(14, w // 60)
    font = _font(size)
    pad = size // 2
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = pad * 2, pad * 2
    draw.rounded_rectangle([x, y, x + tw + pad * 2, y + th + pad * 2], radius=pad, fill=(18, 59, 80, 200))
    draw.text((x + pad, y + pad - bbox[1]), text, font=font, fill=(255, 255, 255, 255))


def coastal_scene(width=1600, height=1000, variant="beach", seed=1, label="DEMO IMAGE - replace with a real photo"):
    rnd = random.Random(seed)
    img = Image.new("RGB", (width, height), SAND)
    draw = ImageDraw.Draw(img, "RGBA")
    horizon = int(height * (0.48 if variant != "nature" else 0.42))

    # Sky
    sky_top = {"sunset": (250, 196, 140), "nature": (196, 228, 232)}.get(variant, (176, 222, 230))
    _vertical_gradient(draw, (0, 0, width, horizon), sky_top, (255, 240, 220))

    # Sun
    sx = int(width * rnd.uniform(.62, .8))
    sy = int(horizon * rnd.uniform(.32, .55))
    r = int(min(width, height) * .07)
    draw.ellipse([sx - r * 2, sy - r * 2, sx + r * 2, sy + r * 2], fill=(255, 210, 140, 60))
    draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=SUN)

    # Sea
    _vertical_gradient(draw, (0, horizon, width, height), (20, 150, 160), (0, 96, 112))
    for i in range(14):
        y = horizon + int((height - horizon) * (i / 14) ** 1.4) + 6
        amp = 3 + i
        pts = [(x, y + amp * math.sin(x / (60 + i * 6) + i)) for x in range(0, width + 20, 20)]
        draw.line(pts, fill=(255, 255, 255, 40 + i * 4), width=2)

    # Cliffs (Pipa's coloured cliffs) on the left
    cliff_w = int(width * (0.42 if variant != "boat" else 0.3))
    top_y = horizon - int(height * 0.16)
    pts = [(0, top_y)]
    for x in range(0, cliff_w, max(10, width // 80)):
        pts.append((x, top_y + rnd.randint(-8, 8) + int((x / cliff_w) ** 3 * height * 0.18)))
    pts += [(cliff_w, horizon + int(height * .1)), (0, horizon + int(height * .14))]
    draw.polygon(pts, fill=CLIFF)
    for band in range(5):
        by = top_y + 20 + band * int(height * .035)
        draw.line([(0, by), (cliff_w * (0.85 - band * .08), by + band * 6)], fill=CLIFF_LIGHT + (150,), width=8)
    # Forest on top of cliffs
    for _ in range(40):
        fx = rnd.randint(0, int(cliff_w * .8))
        fr = rnd.randint(int(height * .02), int(height * .045))
        fy = top_y + int((fx / cliff_w) ** 3 * height * 0.18) - fr // 2
        draw.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=FOREST + (230,))

    # Beach strip
    beach_top = height - int(height * .2)
    draw.polygon([(0, beach_top + 40), (width, beach_top - 10), (width, height), (0, height)], fill=(244, 222, 188))
    draw.line([(0, beach_top + 40), (width, beach_top - 10)], fill=(255, 255, 255, 140), width=6)

    if variant == "boat":
        bx, by = int(width * .55), horizon + int((height - horizon) * .38)
        draw.polygon([(bx - 120, by), (bx + 120, by), (bx + 90, by + 40), (bx - 90, by + 40)], fill=(255, 255, 255))
        draw.polygon([(bx - 10, by - 150), (bx - 10, by - 5), (bx + 90, by - 5)], fill=(255, 250, 240))
        draw.line([(bx - 10, by - 160), (bx - 10, by)], fill=OCEAN, width=5)
        # dolphins
        for k in range(2):
            dx, dy = bx - 300 - k * 90, by + 70 + k * 30
            draw.arc([dx - 40, dy - 30, dx + 40, dy + 30], 200, 340, fill=OCEAN, width=10)
    elif variant == "buggy":
        # dunes
        draw.ellipse([int(width * .35), beach_top - 160, int(width * 1.3), beach_top + 300], fill=(240, 205, 150))
        bx, by = int(width * .64), beach_top - 30
        draw.rounded_rectangle([bx - 110, by - 50, bx + 110, by + 10], radius=18, fill=CORAL)
        draw.line([(bx - 70, by - 50), (bx - 30, by - 110), (bx + 60, by - 110), (bx + 80, by - 50)], fill=OCEAN, width=8)
        for wx in (bx - 70, bx + 70):
            draw.ellipse([wx - 32, by - 10, wx + 32, by + 54], fill=OCEAN)
            draw.ellipse([wx - 12, by + 10, wx + 12, by + 34], fill=(220, 220, 220))
    elif variant == "nature":
        for _ in range(28):
            tx = rnd.randint(int(width * .45), width)
            tr = rnd.randint(int(height * .04), int(height * .09))
            ty = horizon - rnd.randint(0, int(height * .05))
            draw.ellipse([tx - tr, ty - tr, tx + tr, ty + tr], fill=_lerp(FOREST, TEAL, rnd.random() * .3) + (235,))
        # natural pools
        for k in range(3):
            px = int(width * (.5 + k * .14))
            draw.ellipse([px - 80, beach_top + 30, px + 80, beach_top + 80], fill=(70, 190, 190))
    elif variant == "car":
        # road
        draw.polygon([(int(width * .3), height), (int(width * .62), beach_top - 30),
                      (int(width * .7), beach_top - 30), (int(width * .95), height)], fill=(90, 98, 104))
        for k in range(6):
            y = beach_top + k * 40
            x = int(width * .66) + (k * 12)
            draw.rectangle([x - 4, y, x + 4, y + 22], fill=(255, 255, 255))
        cx, cy = int(width * .72), height - 140
        draw.rounded_rectangle([cx - 150, cy - 60, cx + 150, cy + 30], radius=24, fill=(250, 250, 250))
        draw.rounded_rectangle([cx - 95, cy - 115, cx + 85, cy - 50], radius=20, fill=(235, 240, 242))
        draw.rectangle([cx - 80, cy - 105, cx + 70, cy - 60], fill=(120, 170, 190))
        for wx in (cx - 90, cx + 90):
            draw.ellipse([wx - 34, cy + 2, wx + 34, cy + 70], fill=OCEAN)

    img = img.filter(ImageFilter.GaussianBlur(0.6))
    if label:
        _label(img, label)
    return img


def scene_bytes(**kwargs):
    buffer = BytesIO()
    coastal_scene(**kwargs).save(buffer, format="JPEG", quality=84, optimize=True, progressive=True)
    return buffer.getvalue()
