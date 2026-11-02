"""CoastalNow Pinterest creative v2: photo-led, useful, evergreen 2:3 pins.

The three formats reinterpret public Pinterest creative guidance (photo + a
clear action-oriented headline + a practical checklist). It uses the already
licensed category photos and the verified CoastalNow logo, not scraped pins.
No live tide/wave numbers, invented spot photography, catch predictions or
safety guarantees are printed. Existing published v1 files are immutable.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from pinterest.render import (
    BOLD_FONT, REGULAR_FONT, WHITE, WIDTH, HEIGHT,
    _draw_website_logo_mark, _font, _load_photo_background,
)

PALETTES = {
    "tides": {
        "accent": (53, 209, 211),
        "paper": (237, 248, 246),
        "label": "TIDE PLANNING",
        "hook": "Plan a low-tide beach walk",
        "panel": "YOUR TIDE CHECKLIST",
        "checks": (
            "Find local high & low tides",
            "Compare the 7-day tide schedule",
            "Check NOAA station coverage",
        ),
        "cta": "EXPLORE THE TIDE CHART",
    },
    "fishing": {
        "accent": (244, 181, 94),
        "paper": (255, 248, 235),
        "label": "SHORE FISHING",
        "hook": "Tide. Wind. Waves.",
        "panel": "BEFORE YOU CAST",
        "checks": (
            "Review NOAA tide timing",
            "Check NWS wind, waves & alerts",
            "Read local shore access notes",
        ),
        "cta": "PLAN YOUR FISHING VISIT",
    },
    "surfing": {
        "accent": (103, 221, 239),
        "paper": (237, 249, 252),
        "label": "SURF CHECK",
        "hook": "Before you paddle out",
        "panel": "CHECK CONDITIONS FIRST",
        "checks": (
            "Compare wave height & period",
            "Review wind & marine alerts",
            "Read area forecast limitations",
        ),
        "cta": "SEE THE SURF OUTLOOK",
    },
}
DARK = (10, 37, 55)
MUTED = (65, 92, 105)


def _fit(draw: ImageDraw.ImageDraw, words: str, max_size: int, min_size: int, width: int):
    for size in range(max_size, min_size - 1, -2):
        font = _font(BOLD_FONT, size)
        if draw.textbbox((0, 0), words, font=font)[2] <= width:
            return font
    return _font(BOLD_FONT, min_size)


def _lines(draw: ImageDraw.ImageDraw, text: str, size: int, max_width: int) -> tuple[list[str], object]:
    """Never clip long city names or draw outside the safe zones."""
    for points in range(size, 47, -2):
        font = _font(BOLD_FONT, points)
        lines: list[str] = []
        current = ""
        for word in text.upper().split():
            trial = (current + " " + word).strip()
            if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        if len(lines) <= 2 and all(draw.textbbox((0, 0), line, font=font)[2] <= max_width for line in lines):
            return lines, font
    raise ValueError(f"Pinterest location title is too long to fit: {text}")


def _photo_base(kind: str, slug: str) -> Image.Image:
    photo = _load_photo_background(kind)
    if sum(map(ord, slug)) % 2:
        photo = ImageOps.mirror(photo)
    canvas = photo.convert("RGBA")
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shade = ImageDraw.Draw(overlay)
    # Bold headline remains readable against unknown coastal-photo luminance.
    for y in range(0, 980):
        alpha = round(202 - 111 * y / 980)
        shade.line((0, y, WIDTH, y), fill=(4, 18, 29, alpha))
    canvas.alpha_composite(overlay)
    return canvas


def _brand(image: Image.Image, draw: ImageDraw.ImageDraw, accent: tuple[int, int, int]) -> None:
    _draw_website_logo_mark(image, 64, 65, 49)
    draw.text((130, 70), "CoastalNow", font=_font(BOLD_FONT, 37), fill=WHITE)
    draw.rounded_rectangle((705, 69, 942, 120), radius=25, fill=(8, 40, 54))
    draw.text((730, 81), "COASTAL GUIDE", font=_font(BOLD_FONT, 24), fill=accent)


def render_pin_v2(item: dict, kind: str, output: Path) -> Path:
    """Render one immutable Pinterest image. All image copy is date-independent."""
    if kind not in PALETTES:
        raise ValueError(f"Unsupported Pinterest kind: {kind}")
    palette = PALETTES[kind]
    accent = palette["accent"]
    canvas = _photo_base(kind, item["slug"])
    draw = ImageDraw.Draw(canvas)
    _brand(canvas, draw, accent)

    # Headline order: location first, then the user's practical reason to click.
    draw.rectangle((66, 176, 150, 185), fill=accent)
    draw.text((66, 202), palette["label"], font=_font(BOLD_FONT, 32), fill=accent)

    lines, city_font = _lines(draw, item["name"], 136, 860)
    y = 270
    for line in lines:
        draw.text((60, y), line, font=city_font, fill=WHITE, stroke_width=1, stroke_fill=(3, 18, 26))
        y += city_font.size + 11
    state_font = _fit(draw, item["state"], 39, 25, 800)
    draw.text((66, y + 3), item["state"], font=state_font, fill=(220, 239, 244))
    hook_font = _fit(draw, palette["hook"], 52, 29, 865)
    hook_y = max(595, y + 79)
    draw.rounded_rectangle((64, hook_y - 14, 939, hook_y + 76), radius=21, fill=(8, 38, 50))
    draw.text((88, hook_y + 1), palette["hook"], font=hook_font, fill=WHITE)

    # Photo occupies more than half the Pin. Lower field summarizes real utility.
    paper = palette["paper"]
    draw.rounded_rectangle((0, 898, 1000, 1535), radius=48, fill=paper)
    draw.rectangle((0, 961, 1000, 1500), fill=paper)
    draw.rectangle((65, 959, 151, 967), fill=accent)
    draw.text((65, 995), palette["panel"], font=_font(BOLD_FONT, 45), fill=DARK)

    for i, line in enumerate(palette["checks"]):
        yy = 1093 + i * 79
        draw.ellipse((65, yy + 11, 91, yy + 37), fill=accent)
        draw.line([(72, yy + 24), (78, yy + 30), (89, yy + 16)], fill=DARK, width=3)
        label_font = _fit(draw, line, 34, 25, 817)
        draw.text((114, yy), line, font=label_font, fill=DARK)

    button = (64, 1358, 936, 1442)
    draw.rounded_rectangle(button, radius=20, fill=DARK)
    cta = palette["cta"]
    cta_font = _fit(draw, cta, 34, 25, 790)
    draw.text((93, 1382), cta, font=cta_font, fill=WHITE)
    draw.text((884, 1377), "→", font=_font(BOLD_FONT, 44), fill=accent)
    draw.text((65, 1456), "coastalnowtides.com", font=_font(BOLD_FONT, 25), fill=MUTED)
    draw.text((651, 1457), "PHOTO: ILLUSTRATIVE", font=_font(REGULAR_FONT, 20), fill=MUTED)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    return output
