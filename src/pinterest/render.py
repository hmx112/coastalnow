"""Photographic 1000x1500 CoastalNow Pinterest poster renderer."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH = 1000
HEIGHT = 1500

WHITE = (255, 255, 255)
NAVY = (7, 23, 38)
GOLD = (232, 177, 107)
GOLD_LIGHT = (242, 200, 142)

BOLD_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
REGULAR_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
SERIF_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
SERIF_ITALIC_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf")

# Fixed free-to-use Unsplash photographs. The URLs are intentionally stable and
# category-specific; generated Pinterest PNGs remain immutable after first publish.
PHOTO_BACKGROUNDS = {
    "surfing": {
        "url": "https://images.unsplash.com/photo-1612806237422-64509788033d?auto=format&fit=crop&w=1600&h=2400&q=85",
        "credit": "Woody Kelly / Unsplash",
    },
    "fishing": {
        "url": "https://images.unsplash.com/photo-1645357292577-3720b0d65258?auto=format&fit=crop&w=1600&h=2400&q=85",
        "credit": "Vince Russell / Unsplash",
    },
    "tides": {
        "url": "https://images.unsplash.com/photo-1779844383248-79980909cd8a?auto=format&fit=crop&w=1600&h=2400&q=85",
        "credit": "Dan Begel / Unsplash",
    },
}

_FALLBACK_GRADIENTS = {
    "surfing": ((18, 79, 111), (4, 23, 40)),
    "fishing": ((91, 91, 103), (21, 30, 44)),
    "tides": ((31, 88, 117), (6, 27, 43)),
}

_PHOTO_CACHE: dict[str, Image.Image] = {}


def pin_text(item: dict, kind: str) -> dict[str, str]:
    if kind not in {"tides", "fishing", "surfing"}:
        raise ValueError(f"Unsupported Pinterest pin kind: {kind}")

    base = {
        "brand": "CoastalNow",
        "location": item["name"].upper(),
        "state": item["state"],
    }
    if kind == "surfing":
        return {
            **base,
            "category": "SURF CONDITIONS",
            "subtitle": "Surf Conditions & Best Times",
            "cta": "View Surf Conditions",
        }
    if kind == "fishing":
        return {
            **base,
            "category": "FISHING CONDITIONS",
            "subtitle": "Fishing Conditions & Best Times",
            "cta": "View Fishing Conditions",
        }
    return {
        **base,
        "category": "TIDE TIMES",
        "subtitle": "Tide Times & Tide Chart",
        "cta": "View Tide Times",
    }


def _font(path: Path, size: int):
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_size: int,
    min_size: int,
    max_width: int,
    path: Path = BOLD_FONT,
):
    for size in range(max_size, min_size - 1, -2):
        font = _font(path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _font(path, min_size)


def _centered_x(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return max(0, (WIDTH - (bbox[2] - bbox[0])) // 2)


def _gradient_fallback(kind: str) -> Image.Image:
    top, bottom = _FALLBACK_GRADIENTS[kind]
    image = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / max(1, HEIGHT - 1)
        color = tuple(round(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=color)
    return image


def _load_photo_background(kind: str) -> Image.Image:
    cached = _PHOTO_CACHE.get(kind)
    if cached is not None:
        return cached.copy()

    try:
        request = Request(
            PHOTO_BACKGROUNDS[kind]["url"],
            headers={"User-Agent": "CoastalNow-Pinterest/1.0"},
        )
        with urlopen(request, timeout=15) as response:
            source = Image.open(BytesIO(response.read())).convert("RGB")
        image = ImageOps.fit(source, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    except Exception:
        # Network/CDN failure must not break the daily publishing workflow or
        # reintroduce the old low-fidelity vector-character artwork.
        image = _gradient_fallback(kind)

    _PHOTO_CACHE[kind] = image.copy()
    return image


def _overlay_readability(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Dark top for large category/location typography.
    for y in range(0, 760):
        alpha = max(10, round(180 * (1 - y / 760)))
        draw.line((0, y, WIDTH, y), fill=(3, 15, 26, alpha))

    # Dark lower fade for one subtitle and one CTA only.
    for y in range(1080, HEIGHT):
        alpha = min(220, round(30 + (y - 1080) / 420 * 190))
        draw.line((0, y, WIDTH, y), fill=(2, 13, 24, alpha))

    image.alpha_composite(overlay)
    return image


def _draw_coastalnow_brand(draw: ImageDraw.ImageDraw) -> None:
    brand = "CoastalNow"
    font = _font(SERIF_FONT, 47)
    x = _centered_x(draw, brand, font)
    draw.text((x, 72), brand, font=font, fill=WHITE, stroke_width=1, stroke_fill=(0, 0, 0))


def _draw_heading(draw: ImageDraw.ImageDraw, text: dict[str, str]) -> None:
    _draw_coastalnow_brand(draw)

    category = text["category"]
    category_font = _fit_font(draw, category, 112, 62, 900)
    category_x = _centered_x(draw, category, category_font)
    draw.text((category_x, 168), category, font=category_font, fill=GOLD, stroke_width=1, stroke_fill=(67, 36, 12))

    line_y = 344
    draw.line((105, line_y, 895, line_y), fill=(233, 187, 126, 190), width=2)

    location = text["location"]
    location_font = _fit_font(draw, location, 190, 54, 910)
    location_x = _centered_x(draw, location, location_font)
    draw.text((location_x, 380), location, font=location_font, fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0))
    location_bbox = draw.textbbox((location_x, 380), location, font=location_font)

    state = text["state"]
    state_font = _fit_font(draw, state, 58, 34, 620, SERIF_ITALIC_FONT)
    state_x = _centered_x(draw, state, state_font)
    state_y = min(690, location_bbox[3] + 12)
    draw.line((165, state_y + 30, state_x - 28, state_y + 30), fill=(233, 187, 126, 180), width=2)
    draw.line((state_x + draw.textbbox((0, 0), state, font=state_font)[2] + 28, state_y + 30, 835, state_y + 30), fill=(233, 187, 126, 180), width=2)
    draw.text((state_x, state_y), state, font=state_font, fill=WHITE, stroke_width=1, stroke_fill=(0, 0, 0))


def _draw_footer(draw: ImageDraw.ImageDraw, text: dict[str, str]) -> None:
    subtitle = text["subtitle"]
    subtitle_font = _fit_font(draw, subtitle, 40, 28, 860, SERIF_FONT)
    subtitle_x = _centered_x(draw, subtitle, subtitle_font)
    draw.text((subtitle_x, 1224), subtitle, font=subtitle_font, fill=WHITE, stroke_width=1, stroke_fill=(0, 0, 0))

    button = (214, 1322, 786, 1444)
    draw.rounded_rectangle(button, radius=32, fill=GOLD_LIGHT)
    cta = text["cta"]
    cta_font = _fit_font(draw, cta, 42, 29, button[2] - button[0] - 70)
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_width = cta_bbox[2] - cta_bbox[0]
    cta_height = cta_bbox[3] - cta_bbox[1]
    cta_x = (WIDTH - cta_width) // 2
    cta_y = button[1] + ((button[3] - button[1]) - cta_height) // 2 - cta_bbox[1]
    draw.text((cta_x, cta_y), cta, font=cta_font, fill=(31, 25, 16))


def render_pin(item: dict, kind: str, output: Path) -> Path:
    text = pin_text(item, kind)
    image = _overlay_readability(_load_photo_background(kind))
    draw = ImageDraw.Draw(image)
    _draw_heading(draw, text)
    _draw_footer(draw, text)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output
