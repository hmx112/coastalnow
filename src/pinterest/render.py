"""Deterministic 1000x1500 CoastalNow Pinterest image renderer."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1000
HEIGHT = 1500

OFF_WHITE = (244, 248, 245)
SEAFOAM = (191, 231, 222)
TEAL = (23, 139, 145)
DEEP_TEAL = (8, 92, 105)
NAVY = (8, 45, 76)
SUN = (246, 212, 134)
MUTED = (64, 97, 103)

BOLD_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
REGULAR_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def pin_text(item: dict, kind: str) -> dict[str, str]:
    if kind not in {"tides", "fishing"}:
        raise ValueError(f"Unsupported Pinterest pin kind: {kind}")
    if kind == "tides":
        category = "TIDE TIMES & TIDE CHART"
        footer = "Live coastal data on CoastalNow"
    else:
        category = "FISHING CONDITIONS & BEST TIMES"
        footer = "Live tide, wind & wave context"
    return {
        "brand": "CoastalNow",
        "location": item["name"].upper(),
        "state": item["state"].upper(),
        "category": category,
        "footer": footer,
    }


def _font(path: Path, size: int):
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _fit_font(draw: ImageDraw.ImageDraw, text: str, path: Path, max_size: int, min_size: int, max_width: int):
    for size in range(max_size, min_size - 1, -2):
        font = _font(path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _font(path, min_size)


def _wave_polygon(base_y: int, amplitude: int, phase: float, step: int = 16) -> list[tuple[int, int]]:
    points = [(0, HEIGHT)]
    for x in range(0, WIDTH + step, step):
        y = base_y + int(amplitude * math.sin((x / WIDTH) * math.tau + phase))
        points.append((x, y))
    points.append((WIDTH, HEIGHT))
    return points


def _draw_wave_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int]) -> None:
    cx, cy = center
    draw.arc((cx - 70, cy - 45, cx + 70, cy + 85), 190, 355, fill=OFF_WHITE, width=10)
    draw.arc((cx - 50, cy - 20, cx + 65, cy + 70), 205, 350, fill=SEAFOAM, width=8)


def render_pin(item: dict, kind: str, output: Path) -> Path:
    text = pin_text(item, kind)
    image = Image.new("RGB", (WIDTH, HEIGHT), OFF_WHITE)
    draw = ImageDraw.Draw(image)

    # Brand/header field.
    draw.rectangle((0, 0, WIDTH, 210), fill=NAVY)
    draw.ellipse((72, 60, 172, 160), fill=TEAL)
    _draw_wave_icon(draw, (122, 105))
    brand_font = _font(BOLD_FONT, 54)
    draw.text((205, 75), text["brand"], fill=OFF_WHITE, font=brand_font)
    draw.text((205, 137), "COASTAL CONDITIONS", fill=SEAFOAM, font=_font(REGULAR_FONT, 23))

    # Horizon/sun motif.
    draw.ellipse((710, 300, 890, 480), fill=SUN)
    draw.rectangle((0, 430, WIDTH, 438), fill=SEAFOAM)

    # Main text hierarchy.
    location_font = _fit_font(draw, text["location"], BOLD_FONT, 118, 62, 840)
    state_font = _fit_font(draw, text["state"], BOLD_FONT, 42, 28, 840)
    category_font = _fit_font(draw, text["category"], BOLD_FONT, 48, 30, 820)

    draw.text((80, 310), text["location"], fill=NAVY, font=location_font)
    location_bbox = draw.textbbox((80, 310), text["location"], font=location_font)
    state_y = location_bbox[3] + 20
    draw.text((84, state_y), text["state"], fill=DEEP_TEAL, font=state_font)

    category_y = max(640, state_y + 115)
    draw.rounded_rectangle((70, category_y - 28, 930, category_y + 150), radius=32, fill=(227, 242, 237))
    draw.text((100, category_y + 18), text["category"], fill=NAVY, font=category_font)

    # Layered coastal graphic, kept abstract and evergreen.
    draw.polygon(_wave_polygon(1030, 55, 0.2), fill=SEAFOAM)
    draw.polygon(_wave_polygon(1110, 70, 1.8), fill=TEAL)
    draw.polygon(_wave_polygon(1215, 52, 3.0), fill=DEEP_TEAL)
    draw.polygon(_wave_polygon(1320, 42, 4.2), fill=NAVY)

    # Simple vertical marker gives Tide/Fishing templates a distinct visual cue without icons/logos.
    if kind == "tides":
        draw.line((115, 895, 115, 1060), fill=DEEP_TEAL, width=10)
        draw.line((92, 930, 138, 930), fill=DEEP_TEAL, width=8)
        draw.line((92, 985, 138, 985), fill=DEEP_TEAL, width=8)
    else:
        draw.arc((82, 880, 200, 1000), 205, 355, fill=DEEP_TEAL, width=10)
        draw.line((188, 932, 230, 1018), fill=DEEP_TEAL, width=8)
        draw.ellipse((222, 1010, 238, 1026), fill=DEEP_TEAL)

    footer_font = _fit_font(draw, text["footer"], REGULAR_FONT, 31, 22, 820)
    footer_bbox = draw.textbbox((0, 0), text["footer"], font=footer_font)
    footer_width = footer_bbox[2] - footer_bbox[0]
    draw.text(((WIDTH - footer_width) / 2, 1432), text["footer"], fill=OFF_WHITE, font=footer_font)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    return output
