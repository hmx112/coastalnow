"""Pinterest-first 1000x1500 CoastalNow poster renderer."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1000
HEIGHT = 1500

WHITE = (255, 255, 255)
NAVY = (7, 31, 55)
TEAL = (19, 154, 161)
MUTED_WHITE = (227, 241, 240)

BOLD_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
REGULAR_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def pin_text(item: dict, kind: str) -> dict[str, object]:
    if kind not in {"tides", "fishing", "surfing"}:
        raise ValueError(f"Unsupported Pinterest pin kind: {kind}")

    base = {
        "brand": "CoastalNow",
        "location": item["name"].upper(),
        "state": item["state"].upper(),
    }

    if kind == "tides":
        return {
            **base,
            "category": "TIDE TIMES & TIDE CHART",
            "headline_lines": ("TIDE TIMES &", "TIDE CHART"),
            "subtitle": "Fast local tide info for planning by the water.",
            "features": (
                ("High & Low Tide Times", "Know when tides rise and fall."),
                ("7-Day Tide Forecast", "Plan ahead with a weekly outlook."),
                ("Live NOAA Tide Data", "Reliable local prediction data."),
                ("Today’s Tide Chart", "See the tide pattern at a glance."),
            ),
            "feature_icons": ("tide", "calendar", "data", "chart"),
            "cta": "See today’s tide times →",
            "footer": "Your go-to source for coastal conditions.",
            "scene": "tides",
        }

    if kind == "fishing":
        return {
            **base,
            "category": "FISHING CONDITIONS & BEST TIMES",
            "headline_lines": ("FISHING CONDITIONS", "& BEST TIMES"),
            "subtitle": "For shore, pier and nearshore fishing.",
            "features": (
                ("Live 0–100 Fishing Score", "See how conditions rate for fishing."),
                ("Tide", "Tide movement and timing"),
                ("Wind", "Wind speed and direction"),
                ("Waves", "Wave height and period"),
                ("Weather", "Sky, rain chance and more"),
                ("Best 3-hour fishing window", "Top window based on today’s conditions"),
            ),
            "feature_icons": ("score", "tide", "wind", "waves", "weather", "window"),
            "cta": "See today’s fishing conditions →",
            "footer": "Live tide, wind & wave context",
            "scene": "fishing",
        }

    return {
        **base,
        "category": "SURF CONDITIONS & BEST TIMES",
        "headline_lines": ("SURF CONDITIONS", "& BEST TIMES"),
        "subtitle": "Wave, wind and weather context for coastal surf planning.",
        "features": (
            ("Wave & Swell Context", "Wave height and period context"),
            ("Wind & Weather", "Wind, rain and sky conditions"),
            ("Surf Planning Window", "Best 3-hour planning window"),
            ("NWS Alert Context", "Official warnings always take priority"),
        ),
        "feature_icons": ("waves", "wind", "window", "alert"),
        "cta": "See current surf conditions →",
        "footer": "Wave, wind & weather context",
        "scene": "surfing",
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


def _gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        progress = y / (HEIGHT - 1)
        color = tuple(
            round(top[index] * (1 - progress) + bottom[index] * progress)
            for index in range(3)
        )
        draw.line((0, y, WIDTH, y), fill=color)
    return image


def _sine_points(
    x1: int,
    x2: int,
    y: int,
    amplitude: int,
    cycles: float = 1.5,
    step: int = 4,
) -> list[tuple[int, int]]:
    width = max(1, x2 - x1)
    points = []
    for x in range(x1, x2 + 1, step):
        phase = ((x - x1) / width) * math.tau * cycles
        points.append((x, y + int(math.sin(phase) * amplitude)))
    return points


def _draw_tide_scene(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    draw.ellipse((655, 205, 930, 480), fill=(255, 188, 104))
    draw.polygon(
        [(0, 690), (145, 575), (260, 625), (365, 540), (520, 620), (600, 740), (0, 820)],
        fill=(8, 64, 82),
    )
    draw.polygon([(0, 680), (1000, 650), (1000, 1040), (0, 1040)], fill=(24, 137, 153))
    for y, amplitude, color, width in (
        (745, 22, (113, 232, 219), 11),
        (805, 28, WHITE, 14),
        (890, 18, (91, 212, 204), 10),
        (975, 25, WHITE, 13),
    ):
        draw.line(_sine_points(-40, 1040, y, amplitude, 2.3), fill=color, width=width)
    for radius in (88, 55, 26):
        draw.ellipse(
            (785 - radius, 755 - radius, 785 + radius, 755 + radius),
            outline=(223, 250, 245),
            width=4,
        )


def _draw_fishing_scene(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    draw.ellipse((105, 210, 365, 470), fill=(255, 183, 86))
    draw.polygon([(0, 690), (1000, 665), (1000, 1040), (0, 1040)], fill=(20, 111, 132))
    for y in (760, 840, 930):
        draw.line(_sine_points(-30, 1030, y, 18, 2.0), fill=(183, 233, 220), width=8)

    # Pier and angler silhouette: a strong category-specific focal image.
    draw.polygon([(515, 610), (1000, 560), (1000, 710), (520, 720)], fill=(11, 37, 48))
    for x in (580, 700, 825, 940):
        draw.rectangle((x, 690, x + 18, 965), fill=(11, 37, 48))
    draw.ellipse((625, 507, 663, 545), fill=(8, 26, 36))
    draw.line((644, 545, 638, 625), fill=(8, 26, 36), width=18)
    draw.line((641, 575, 596, 610), fill=(8, 26, 36), width=12)
    draw.line((641, 575, 683, 607), fill=(8, 26, 36), width=12)
    draw.line((638, 620, 608, 674), fill=(8, 26, 36), width=13)
    draw.line((638, 620, 665, 674), fill=(8, 26, 36), width=13)
    draw.line((680, 606, 792, 457), fill=(8, 26, 36), width=5)
    draw.arc((770, 453, 955, 790), 260, 20, fill=(225, 239, 231), width=3)


def _draw_surfing_scene(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    draw.ellipse((675, 175, 940, 440), fill=(255, 184, 112))
    draw.polygon([(0, 665), (1000, 610), (1000, 1065), (0, 1065)], fill=(20, 128, 164))

    # Large curling wave and surfer silhouette create a Pinterest-first visual hook.
    draw.polygon(
        [(80, 965), (120, 785), (230, 650), (385, 570), (565, 590), (715, 700), (815, 865), (740, 1015)],
        fill=(24, 177, 190),
    )
    draw.ellipse((410, 620, 790, 1000), fill=(8, 80, 121))
    draw.pieslice((365, 565, 830, 1050), 198, 355, fill=(38, 192, 198))
    draw.ellipse((500, 705, 790, 1010), fill=(9, 76, 113))
    for y, amplitude in ((665, 15), (720, 20), (775, 17), (945, 23)):
        draw.line(_sine_points(160, 830, y, amplitude, 1.4), fill=WHITE, width=14)

    center_x, center_y = 555, 825
    draw.ellipse((center_x - 16, center_y - 58, center_x + 16, center_y - 26), fill=(6, 26, 40))
    draw.line((center_x, center_y - 25, center_x - 4, center_y + 32), fill=(6, 26, 40), width=14)
    draw.line((center_x - 2, center_y - 4, center_x - 48, center_y + 18), fill=(6, 26, 40), width=10)
    draw.line((center_x - 2, center_y - 2, center_x + 47, center_y - 19), fill=(6, 26, 40), width=10)
    draw.line((center_x - 3, center_y + 27, center_x - 41, center_y + 66), fill=(6, 26, 40), width=11)
    draw.line((center_x - 3, center_y + 27, center_x + 38, center_y + 62), fill=(6, 26, 40), width=11)
    draw.arc((center_x - 90, center_y + 42, center_x + 100, center_y + 84), 185, 350, fill=(244, 248, 239), width=10)


def _draw_coastalnow_brand(draw: ImageDraw.ImageDraw, x: int, y: int, inverse: bool = True) -> None:
    mark_fill = WHITE if inverse else TEAL
    wave_fill = TEAL if inverse else WHITE
    draw.rounded_rectangle((x, y, x + 68, y + 68), radius=18, fill=mark_fill)
    for wave_y in (y + 23, y + 34, y + 45):
        draw.line(_sine_points(x + 14, x + 54, wave_y, 3, 1.25, 2), fill=wave_fill, width=4)
    brand_font = _font(BOLD_FONT, 42)
    draw.text((x + 88, y + 6), "CoastalNow", fill=WHITE if inverse else NAVY, font=brand_font)


def _draw_common_heading(draw: ImageDraw.ImageDraw, text: dict[str, object]) -> None:
    _draw_coastalnow_brand(draw, 58, 50, True)

    category = str(text["category"])
    category_font = _fit_font(draw, category, 27, 20, 720)
    category_bbox = draw.textbbox((0, 0), category, font=category_font)
    category_width = category_bbox[2] - category_bbox[0]
    draw.rounded_rectangle((58, 150, 86 + category_width, 205), radius=26, fill=WHITE)
    draw.text((72, 162), category, fill=NAVY, font=category_font)

    location = str(text["location"])
    location_font = _fit_font(draw, location, 88, 54, 880)
    draw.text((58, 245), location, fill=WHITE, font=location_font, stroke_width=2, stroke_fill=(0, 0, 0))
    location_bbox = draw.textbbox((58, 245), location, font=location_font)
    state_y = location_bbox[3] + 2
    state_font = _fit_font(draw, str(text["state"]), 30, 22, 600, REGULAR_FONT)
    draw.text((62, state_y), str(text["state"]), fill=MUTED_WHITE, font=state_font)


def _draw_bottom_panel(image: Image.Image, text: dict[str, object], kind: str) -> None:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(880, HEIGHT):
        alpha = min(240, int(20 + (y - 880) / 620 * 220))
        overlay_draw.rectangle((0, y, WIDTH, y + 1), fill=(4, 23, 38, alpha))
    image.alpha_composite(overlay)

    draw = ImageDraw.Draw(image)
    cursor_y = 930
    for line in text["headline_lines"]:
        line_text = str(line)
        line_font = _fit_font(draw, line_text, 66, 46, 884)
        draw.text((58, cursor_y), line_text, font=line_font, fill=WHITE, stroke_width=1, stroke_fill=(0, 0, 0))
        bbox = draw.textbbox((58, cursor_y), line_text, font=line_font)
        cursor_y = bbox[3] + 2

    subtitle = str(text["subtitle"])
    subtitle_font = _fit_font(draw, subtitle, 29, 21, 870, REGULAR_FONT)
    draw.text((62, cursor_y + 18), subtitle, font=subtitle_font, fill=(222, 239, 239))

    chip_y = cursor_y + 87
    chip_width = 282
    if kind == "tides":
        labels = ("HIGH + LOW", "7-DAY VIEW", "NOAA DATA")
    elif kind == "fishing":
        labels = ("FISHING SCORE", "TIDE + WIND", "BEST WINDOW")
    else:
        labels = ("WAVE + SWELL", "WIND + WEATHER", "BEST WINDOW")

    for index, label in enumerate(labels):
        x = 58 + index * (chip_width + 16)
        draw.rounded_rectangle((x, chip_y, x + chip_width, chip_y + 70), radius=22, fill=(255, 255, 255, 235))
        label_font = _fit_font(draw, label, 23, 18, chip_width - 28)
        draw.text((x + 14, chip_y + 21), label, font=label_font, fill=NAVY)

    cta_y = chip_y + 98
    draw.rounded_rectangle((58, cta_y, 942, cta_y + 94), radius=28, fill=(35, 193, 190, 255))
    cta = str(text["cta"])
    cta_font = _fit_font(draw, cta, 33, 24, 820)
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    text_width = cta_bbox[2] - cta_bbox[0]
    draw.text(((WIDTH - text_width) // 2, cta_y + 27), cta, font=cta_font, fill=NAVY)

    footer = str(text["footer"])
    footer_font = _fit_font(draw, footer, 23, 18, 850, REGULAR_FONT)
    draw.text((62, 1450), footer, font=footer_font, fill=(190, 216, 219))


def render_pin(item: dict, kind: str, output: Path) -> Path:
    text = pin_text(item, kind)
    if kind == "tides":
        image = _gradient((30, 94, 120), NAVY)
        _draw_tide_scene(image)
    elif kind == "fishing":
        image = _gradient((74, 76, 91), NAVY)
        _draw_fishing_scene(image)
    elif kind == "surfing":
        image = _gradient((20, 103, 156), (5, 32, 73))
        _draw_surfing_scene(image)
    else:
        raise ValueError(f"Unsupported Pinterest pin kind: {kind}")

    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    _draw_common_heading(draw, text)
    _draw_bottom_panel(image, text, kind)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output
