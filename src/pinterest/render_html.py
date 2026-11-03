"""Safe, deterministic HTML document compiler for Pinterest's 1000x1500 covers.

Images are assembled locally from existing CoastalNow category photographs (or
their offline gradient fallback). Chromium receives fully self-contained HTML:
no external font, CSS, JS, telemetry or image requests are made by the browser.
"""
from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageOps

from pinterest.render import _load_photo_background, PHOTO_BACKGROUNDS

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
KINDS = frozenset(("tides", "fishing", "surfing"))
WIDTH = 1000
HEIGHT = 1500

# U.S. states represented in the coast catalog; location label must remain compact.
STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "california": "CA",
    "connecticut": "CT", "delaware": "DE", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "mississippi": "MS", "new hampshire": "NH", "new jersey": "NJ",
    "new york": "NY", "north carolina": "NC", "oregon": "OR",
    "rhode island": "RI", "south carolina": "SC", "texas": "TX",
    "virginia": "VA", "washington": "WA",
}

LOGO_SVG = (
    '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" '
    'stroke="white" stroke-width="1.8" stroke-linecap="round">'
    '<path d="M3 8c3.5-4 6.5 4 10 0s6.5 4 8 0'
    'M3 13c3.5-4 6.5 4 10 0s6.5 4 8 0'
    'M3 18c3.5-4 6.5 4 10 0s6.5 4 8 0"/></svg>'
)


def _safe_title(name: str) -> tuple[str, str]:
    text = str(name).strip()
    if not text or len(text) > 80:
        raise ValueError("A non-empty coastal location name (max 80 chars) is required")
    # CSS handles normal short city names plus longer multiword city names.
    compact = "verylong" if len(text) > 19 else ("long" if len(text) > 12 else "")
    return escape(text.upper(), quote=True), compact


def _photo_data_uri(kind: str, background: Image.Image | None = None) -> str:
    if background is None:
        # Reuse the already configured legal photo sources and network fallback.
        background = _load_photo_background(kind)
    prepared = ImageOps.fit(background.convert("RGB"), (WIDTH, HEIGHT),
                            method=Image.Resampling.LANCZOS)
    buffer = BytesIO()
    prepared.save(buffer, format="JPEG", quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def render_html_document(item: dict, kind: str, *, background: Image.Image | None = None) -> str:
    if kind not in KINDS:
        raise ValueError(f"Unknown Pinterest category: {kind}")
    city, size_class = _safe_title(item["name"])
    raw_state = str(item["state"]).strip()
    if not raw_state:
        raise ValueError("State name must not be empty")
    state = escape(raw_state.upper(), quote=True)
    state_code = escape(STATE_CODES.get(raw_state.casefold(), raw_state.upper()), quote=True)
    template = (TEMPLATES / f"pin_{kind}.html").read_text(encoding="utf-8")
    styles = (TEMPLATES / "pin.css").read_text(encoding="utf-8")
    values = {
        "STYLES": styles,
        "CITY": city,
        "STATE": state,
        "STATE_CODE": state_code,
        "CITY_CLASS": size_class,
        "PHOTO_DATA": _photo_data_uri(kind, background),
        "LOGO": LOGO_SVG,
    }
    for name, value in values.items():
        template = template.replace("{{" + name + "}}", value)
    unresolved = re.findall(r"\{\{[A-Z_]+\}\}", template)
    if unresolved:
        raise ValueError(f"Unresolved Pinterest template substitutions: {unresolved}")
    return template
