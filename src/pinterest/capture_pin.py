"""Render self-contained Pinterest HTML magazine covers with local Chrome.

The GitHub Actions Ubuntu image already provides Google Chrome. Using that
system browser avoids downloading Playwright's ~100MB browser on each run.
"""
from __future__ import annotations

import os
from pathlib import Path
from shutil import which

from PIL import Image

from pinterest.render_html import render_html_document, WIDTH, HEIGHT


def _launch_chromium(playwright):
    # Respect local developer installs while preferring the runner's Chrome.
    requested = os.environ.get("COASTALNOW_CHROME_EXECUTABLE")
    available = requested or which("google-chrome") or which("google-chrome-stable")
    if available:
        return playwright.chromium.launch(executable_path=available, headless=True,
                                          args=["--no-sandbox", "--disable-dev-shm-usage"])
    local = which("chromium") or which("chromium-browser")
    if local:
        return playwright.chromium.launch(executable_path=local, headless=True,
                                          args=["--no-sandbox", "--disable-dev-shm-usage"])
    # Fallback to a previously installed Playwright Chromium if present.
    # If unavailable, fail instead of silently producing a low-quality image.
    return playwright.chromium.launch(headless=True, args=["--no-sandbox"])


def render_pin_html(item: dict, kind: str, output: Path) -> Path:
    """Capture an exact 1000x1500 image with no browser-side network requests."""
    from playwright.sync_api import sync_playwright

    output = Path(output)
    if output.exists():
        # Previously published Pinterest images are immutable.
        return output

    document = render_html_document(item, kind)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".pending.png")
    try:
        with sync_playwright() as playwright:
            browser = _launch_chromium(playwright)
            try:
                page = browser.new_page(
                    viewport={"width": WIDTH, "height": HEIGHT},
                    device_scale_factor=1,
                    reduced_motion="reduce",
                    color_scheme="light",
                )
                page.set_content(document, wait_until="load", timeout=30000)
                page.evaluate("() => document.fonts.ready.then(() => true)")
                dimensions = page.locator(".pin").bounding_box()
                if not dimensions or abs(dimensions["width"] - WIDTH) > 0.5 or abs(dimensions["height"] - HEIGHT) > 0.5:
                    raise ValueError(f"Unexpected Pinterest template dimensions: {dimensions}")
                page.screenshot(path=str(temporary), type="png",
                                full_page=False, animations="disabled")
                page.close()
            finally:
                browser.close()
        with Image.open(temporary) as generated:
            if generated.format != "PNG" or generated.size != (WIDTH, HEIGHT):
                raise ValueError(f"Invalid Pinterest screenshot output: {generated.size}")
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output
