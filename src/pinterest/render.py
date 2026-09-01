"""Deterministic 1000x1500 CoastalNow Pinterest image renderer."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1000
HEIGHT = 1500

OFF_WHITE = (247, 250, 249)
PANEL = (255, 255, 255)
PALE_AQUA = (234, 246, 246)
SEAFOAM = (190, 232, 224)
TEAL = (20, 151, 158)
DEEP_TEAL = (9, 112, 122)
NAVY = (8, 45, 76)
MUTED = (76, 101, 113)
LINE = (216, 233, 232)
SOFT_SHADOW = (226, 237, 236)

BOLD_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
REGULAR_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def pin_text(item: dict, kind: str) -> dict[str, object]:
    if kind not in {"tides", "fishing"}:
        raise ValueError(f"Unsupported Pinterest pin kind: {kind}")

    if kind == "tides":
        return {
            "brand": "CoastalNow",
            "location": item["name"].upper(),
            "state": item["state"].upper(),
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
        }

    return {
        "brand": "CoastalNow",
        "location": item["name"].upper(),
        "state": item["state"].upper(),
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
    }


def _font(path: Path, size: int):
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    path: Path,
    max_size: int,
    min_size: int,
    max_width: int,
):
    for size in range(max_size, min_size - 1, -2):
        font = _font(path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _font(path, min_size)


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    path: Path,
    max_size: int,
    min_size: int,
    max_width: int,
    max_height: int,
    spacing: int = 6,
) -> tuple[object, list[str], int]:
    for size in range(max_size, min_size - 1, -2):
        font = _font(path, size)
        lines = _wrap_lines(draw, text, font, max_width)
        line_bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_height = line_bbox[3] - line_bbox[1]
        total_height = line_height * len(lines) + spacing * max(0, len(lines) - 1)
        if total_height <= max_height:
            return font, lines, total_height
    font = _font(path, min_size)
    lines = _wrap_lines(draw, text, font, max_width)
    line_bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = line_bbox[3] - line_bbox[1]
    total_height = line_height * len(lines) + spacing * max(0, len(lines) - 1)
    return font, lines, total_height


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    x: int,
    y: int,
    font,
    fill: tuple[int, int, int],
    spacing: int = 6,
    align: str = "left",
    width: int | None = None,
) -> int:
    line_bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = line_bbox[3] - line_bbox[1]
    cursor = y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        tx = x
        if align == "center" and width is not None:
            tx = x + max(0, (width - line_width) // 2)
        draw.text((tx, cursor), line, fill=fill, font=font)
        cursor += line_height + spacing
    return cursor - spacing


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font_path: Path,
    max_size: int,
    min_size: int,
    fill: tuple[int, int, int],
    spacing: int = 6,
    align: str = "left",
) -> int:
    x1, y1, x2, y2 = box
    font, lines, _ = _fit_wrapped(
        draw,
        text,
        font_path,
        max_size,
        min_size,
        x2 - x1,
        y2 - y1,
        spacing,
    )
    return _draw_lines(
        draw,
        lines,
        x1,
        y1,
        font,
        fill,
        spacing=spacing,
        align=align,
        width=x2 - x1,
    )


def _sine_points(x1: int, x2: int, y: int, amplitude: int, cycles: float = 1.5) -> list[tuple[int, int]]:
    width = max(1, x2 - x1)
    points = []
    for x in range(x1, x2 + 1, 3):
        phase = ((x - x1) / width) * math.tau * cycles
        points.append((x, y + int(math.sin(phase) * amplitude)))
    return points


def _draw_coastalnow_brand(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    """Draw the site-style rounded-square three-wave logo and CoastalNow wordmark."""
    mark = (x, y, x + 78, y + 78)
    draw.rounded_rectangle(mark, radius=21, fill=TEAL)
    for wave_y in (y + 25, y + 39, y + 53):
        draw.line(_sine_points(x + 17, x + 61, wave_y, 4, cycles=1.35), fill=OFF_WHITE, width=5)

    brand_font = _font(BOLD_FONT, 51)
    draw.text((x + 101, y + 10), "CoastalNow", fill=NAVY, font=brand_font)


def _draw_icon(draw: ImageDraw.ImageDraw, name: str, center: tuple[int, int], size: int = 58) -> None:
    cx, cy = center
    c = DEEP_TEAL
    w = 5

    if name == "score":
        r = size // 2
        draw.arc((cx - r, cy - r, cx + r, cy + r), 200, 340, fill=c, width=7)
        draw.line((cx, cy, cx + 19, cy - 14), fill=c, width=6)
        draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=c)
        return

    if name == "tide":
        for offset in (-12, 0, 12):
            draw.line(_sine_points(cx - 31, cx + 31, cy + offset, 4, cycles=1.25), fill=c, width=w)
        draw.line((cx, cy - 52, cx, cy - 32), fill=c, width=w)
        draw.line((cx, cy - 52, cx - 8, cy - 43), fill=c, width=w)
        draw.line((cx, cy - 52, cx + 8, cy - 43), fill=c, width=w)
        return

    if name == "wind":
        for offset, length in ((-17, 52), (0, 65), (18, 45)):
            y = cy + offset
            draw.line((cx - 32, y, cx - 5 + length // 3, y), fill=c, width=w)
            draw.arc((cx + 2, y - 14, cx + 32, y + 14), 250, 80, fill=c, width=w)
        return

    if name == "waves":
        draw.arc((cx - 38, cy - 32, cx + 25, cy + 29), 195, 345, fill=c, width=7)
        draw.arc((cx - 7, cy - 22, cx + 42, cy + 25), 145, 300, fill=c, width=6)
        draw.line(_sine_points(cx - 34, cx + 35, cy + 26, 3, cycles=1.25), fill=c, width=5)
        return

    if name == "weather":
        draw.ellipse((cx + 1, cy - 37, cx + 33, cy - 5), outline=c, width=5)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + 17 + int(math.cos(rad) * 23)
            y1 = cy - 21 + int(math.sin(rad) * 23)
            x2 = cx + 17 + int(math.cos(rad) * 31)
            y2 = cy - 21 + int(math.sin(rad) * 31)
            draw.line((x1, y1, x2, y2), fill=c, width=4)
        draw.rounded_rectangle((cx - 35, cy - 8, cx + 27, cy + 27), radius=16, outline=c, width=6)
        draw.ellipse((cx - 25, cy - 22, cx + 3, cy + 7), fill=PALE_AQUA, outline=c, width=5)
        return

    if name == "window":
        r = 31
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=6)
        draw.line((cx, cy, cx, cy - 17), fill=c, width=6)
        draw.line((cx, cy, cx + 15, cy + 9), fill=c, width=6)
        return

    if name == "calendar":
        draw.rounded_rectangle((cx - 34, cy - 30, cx + 34, cy + 31), radius=8, outline=c, width=5)
        draw.line((cx - 34, cy - 10, cx + 34, cy - 10), fill=c, width=5)
        draw.line((cx - 18, cy - 39, cx - 18, cy - 21), fill=c, width=5)
        draw.line((cx + 18, cy - 39, cx + 18, cy - 21), fill=c, width=5)
        for dx in (-17, 0, 17):
            for dy in (3, 18):
                draw.rounded_rectangle((cx + dx - 4, cy + dy - 4, cx + dx + 4, cy + dy + 4), radius=2, fill=c)
        return

    if name == "data":
        draw.ellipse((cx - 31, cy - 31, cx + 18, cy - 13), outline=c, width=5)
        draw.line((cx - 31, cy - 22, cx - 31, cy + 23), fill=c, width=5)
        draw.line((cx + 18, cy - 22, cx + 18, cy + 10), fill=c, width=5)
        draw.arc((cx - 31, cy - 5, cx + 18, cy + 13), 0, 180, fill=c, width=5)
        draw.arc((cx - 31, cy + 10, cx + 18, cy + 28), 0, 180, fill=c, width=5)
        draw.ellipse((cx + 5, cy + 4, cx + 39, cy + 38), fill=PANEL, outline=c, width=5)
        draw.line((cx + 13, cy + 21, cx + 20, cy + 28), fill=c, width=4)
        draw.line((cx + 20, cy + 28, cx + 32, cy + 14), fill=c, width=4)
        return

    if name == "chart":
        points = []
        for i in range(0, 67, 3):
            x = cx - 33 + i
            y = cy + int(math.sin((i / 66) * math.tau * 1.25) * 19)
            points.append((x, y))
        draw.line(points, fill=c, width=5)
        draw.line((cx - 34, cy + 31, cx + 35, cy + 31), fill=c, width=4)
        draw.ellipse((points[-1][0] - 5, points[-1][1] - 5, points[-1][0] + 5, points[-1][1] + 5), fill=c)
        return

    raise ValueError(f"Unsupported Pinterest icon: {name}")


def _draw_feature_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    icon: str,
    title: str,
    description: str,
    compact: bool,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1 + 4, y1 + 7, x2 + 4, y2 + 7), radius=28, fill=SOFT_SHADOW)
    draw.rounded_rectangle(box, radius=28, fill=PANEL, outline=LINE, width=2)

    if compact:
        icon_center = ((x1 + x2) // 2, y1 + 56)
        _draw_icon(draw, icon, icon_center, size=52)
        title_y = y1 + 105
        title_bottom = _draw_wrapped_text(
            draw,
            title,
            (x1 + 19, title_y, x2 - 19, y1 + 184),
            BOLD_FONT,
            28,
            22,
            NAVY,
            spacing=4,
            align="center",
        )
        desc_y = max(title_bottom + 10, y1 + 172)
        _draw_wrapped_text(
            draw,
            description,
            (x1 + 19, desc_y, x2 - 19, y2 - 18),
            REGULAR_FONT,
            20,
            16,
            MUTED,
            spacing=3,
            align="center",
        )
    else:
        icon_center = (x1 + 70, y1 + 78)
        draw.ellipse((x1 + 28, y1 + 36, x1 + 112, y1 + 120), fill=PALE_AQUA)
        _draw_icon(draw, icon, icon_center, size=48)
        title_bottom = _draw_wrapped_text(
            draw,
            title,
            (x1 + 135, y1 + 35, x2 - 22, y1 + 118),
            BOLD_FONT,
            32,
            25,
            NAVY,
            spacing=4,
        )
        _draw_wrapped_text(
            draw,
            description,
            (x1 + 135, max(title_bottom + 8, y1 + 117), x2 - 22, y2 - 25),
            REGULAR_FONT,
            22,
            18,
            MUTED,
            spacing=3,
        )


def _draw_benefit_icon(draw: ImageDraw.ImageDraw, kind: str, cx: int, cy: int) -> None:
    c = DEEP_TEAL
    if kind == "local":
        draw.ellipse((cx - 15, cy - 19, cx + 15, cy + 11), outline=c, width=5)
        draw.polygon([(cx - 12, cy + 5), (cx + 12, cy + 5), (cx, cy + 29)], fill=c)
        draw.ellipse((cx - 5, cy - 10, cx + 5, cy), fill=c)
    elif kind == "accurate":
        draw.polygon([(cx, cy - 24), (cx + 20, cy - 15), (cx + 16, cy + 13), (cx, cy + 27), (cx - 16, cy + 13), (cx - 20, cy - 15)], outline=c)
        draw.line((cx - 8, cy + 1, cx - 1, cy + 9), fill=c, width=4)
        draw.line((cx - 1, cy + 9, cx + 11, cy - 7), fill=c, width=4)
    elif kind == "realtime":
        draw.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), outline=c, width=5)
        draw.line((cx, cy, cx, cy - 13), fill=c, width=4)
        draw.line((cx, cy, cx + 12, cy + 5), fill=c, width=4)
    elif kind == "clear":
        draw.ellipse((cx - 23, cy - 23, cx + 23, cy + 23), outline=c, width=5)
        draw.line((cx - 10, cy, cx - 2, cy + 9), fill=c, width=4)
        draw.line((cx - 2, cy + 9, cx + 13, cy - 10), fill=c, width=4)
    else:
        raise ValueError(kind)


def _draw_common_heading(draw: ImageDraw.ImageDraw, text: dict[str, object]) -> None:
    _draw_coastalnow_brand(draw, 58, 46)

    # Soft coastal accent: abstract corner only, never a chart or measurement.
    draw.polygon([(770, 0), (1000, 0), (1000, 300), (902, 250)], fill=PALE_AQUA)
    draw.ellipse((840, 80, 1050, 290), fill=SEAFOAM)

    location = str(text["location"])
    location_font = _fit_font(draw, location, BOLD_FONT, 103, 62, 870)
    draw.text((58, 175), location, fill=NAVY, font=location_font)
    location_bbox = draw.textbbox((58, 175), location, font=location_font)
    state_y = location_bbox[3] + 8
    state_font = _fit_font(draw, str(text["state"]), BOLD_FONT, 38, 28, 600)
    draw.text((62, state_y), str(text["state"]), fill=DEEP_TEAL, font=state_font)

    headline_lines = tuple(text["headline_lines"])
    headline_y = max(340, state_y + 80)
    headline_font = _font(BOLD_FONT, 67)
    cursor = headline_y
    for line in headline_lines:
        fit = _fit_font(draw, str(line), BOLD_FONT, 67, 48, 885)
        draw.text((58, cursor), str(line), fill=NAVY, font=fit)
        bbox = draw.textbbox((58, cursor), str(line), font=fit)
        cursor = bbox[3] + 2

    subtitle_y = cursor + 18
    _draw_wrapped_text(
        draw,
        str(text["subtitle"]),
        (62, subtitle_y, 935, subtitle_y + 74),
        REGULAR_FONT,
        31,
        23,
        MUTED,
        spacing=4,
    )


def _draw_fishing_template(draw: ImageDraw.ImageDraw, text: dict[str, object]) -> None:
    features = tuple(text["features"])
    icons = tuple(text["feature_icons"])
    card_w = 276
    card_h = 252
    gap_x = 20
    gap_y = 20
    start_x = 56
    start_y = 638

    for index, ((title, description), icon) in enumerate(zip(features, icons)):
        row, col = divmod(index, 3)
        x1 = start_x + col * (card_w + gap_x)
        y1 = start_y + row * (card_h + gap_y)
        _draw_feature_card(
            draw,
            (x1, y1, x1 + card_w, y1 + card_h),
            str(icon),
            str(title),
            str(description),
            compact=True,
        )

    cta_box = (67, 1215, 933, 1325)
    draw.rounded_rectangle(cta_box, radius=30, fill=DEEP_TEAL)
    _draw_wrapped_text(
        draw,
        str(text["cta"]),
        (95, 1245, 905, 1305),
        BOLD_FONT,
        37,
        27,
        OFF_WHITE,
        align="center",
    )

    draw.rectangle((0, 1382, WIDTH, HEIGHT), fill=NAVY)
    for wave_y in (1423, 1437, 1451):
        draw.line(_sine_points(67, 112, wave_y, 3, cycles=1.15), fill=SEAFOAM, width=4)
    _draw_wrapped_text(
        draw,
        str(text["footer"]),
        (135, 1411, 925, 1478),
        REGULAR_FONT,
        27,
        21,
        OFF_WHITE,
        align="left",
    )


def _draw_tide_template(draw: ImageDraw.ImageDraw, text: dict[str, object]) -> None:
    features = tuple(text["features"])
    icons = tuple(text["feature_icons"])
    card_w = 422
    card_h = 205
    gap_x = 22
    gap_y = 22
    start_x = 56
    start_y = 640

    for index, ((title, description), icon) in enumerate(zip(features, icons)):
        row, col = divmod(index, 2)
        x1 = start_x + col * (card_w + gap_x)
        y1 = start_y + row * (card_h + gap_y)
        _draw_feature_card(
            draw,
            (x1, y1, x1 + card_w, y1 + card_h),
            str(icon),
            str(title),
            str(description),
            compact=False,
        )

    benefits_box = (56, 1089, 944, 1195)
    draw.rounded_rectangle(benefits_box, radius=24, fill=PALE_AQUA, outline=LINE, width=2)
    benefit_items = (
        ("local", "Local Focus"),
        ("accurate", "Accurate NOAA Data"),
        ("realtime", "Real-time Updates"),
        ("clear", "Clean & Clear"),
    )
    segment_w = (benefits_box[2] - benefits_box[0]) // 4
    for i, (icon, label) in enumerate(benefit_items):
        sx = benefits_box[0] + i * segment_w
        cx = sx + segment_w // 2
        _draw_benefit_icon(draw, icon, cx, benefits_box[1] + 36)
        _draw_wrapped_text(
            draw,
            label,
            (sx + 10, benefits_box[1] + 67, sx + segment_w - 10, benefits_box[3] - 9),
            BOLD_FONT,
            19,
            15,
            NAVY,
            spacing=2,
            align="center",
        )
        if i:
            draw.line((sx, benefits_box[1] + 18, sx, benefits_box[3] - 18), fill=LINE, width=2)

    cta_box = (150, 1232, 850, 1340)
    draw.rounded_rectangle(cta_box, radius=30, fill=DEEP_TEAL)
    _draw_wrapped_text(
        draw,
        str(text["cta"]),
        (178, 1262, 822, 1320),
        BOLD_FONT,
        37,
        27,
        OFF_WHITE,
        align="center",
    )

    for wave_y in (1410, 1424, 1438):
        draw.line(_sine_points(150, 195, wave_y, 3, cycles=1.15), fill=TEAL, width=4)
    _draw_wrapped_text(
        draw,
        str(text["footer"]),
        (220, 1395, 900, 1470),
        REGULAR_FONT,
        25,
        20,
        MUTED,
    )


def render_pin(item: dict, kind: str, output: Path) -> Path:
    text = pin_text(item, kind)
    image = Image.new("RGB", (WIDTH, HEIGHT), OFF_WHITE)
    draw = ImageDraw.Draw(image)

    _draw_common_heading(draw, text)
    if kind == "tides":
        _draw_tide_template(draw, text)
    elif kind == "fishing":
        _draw_fishing_template(draw, text)
    else:  # pin_text already validates, kept explicit for readability.
        raise ValueError(f"Unsupported Pinterest pin kind: {kind}")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    return output
