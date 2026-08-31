"""IndexNow URL selection and payload helpers for CoastalNow."""
from __future__ import annotations

import xml.etree.ElementTree as ET

BASE_URL = "https://coastalnowtides.com"
HOST = "coastalnowtides.com"
INDEXNOW_KEY = "d9841f79a4de725f16d6ed88c7807a68"
KEY_FILENAME = f"{INDEXNOW_KEY}.txt"
KEY_LOCATION = f"{BASE_URL}/{KEY_FILENAME}"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS_PER_BATCH = 10_000


def public_path_to_url(path: str) -> str | None:
    """Map a deployable public HTML file to its production canonical path."""
    normalized = path.strip().replace("\\", "/")
    if not normalized.startswith("public/") or not normalized.endswith(".html"):
        return None
    relative = normalized[len("public/") :]
    if relative == "index.html":
        return BASE_URL + "/"
    if relative.endswith("/index.html"):
        return BASE_URL + "/" + relative[: -len("index.html")]
    return BASE_URL + "/" + relative


def changed_page_urls(diff_text: str) -> list[str]:
    """Return unique production page URLs represented by a git name-status diff."""
    urls: list[str] = []
    seen: set[str] = set()
    for raw_line in diff_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0][:1]
        if status not in {"A", "M", "D"}:
            continue
        url = public_path_to_url(parts[1])
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def is_bootstrap_diff(diff_text: str) -> bool:
    """Bootstrap once when the public IndexNow ownership key is first added."""
    expected = f"public/{KEY_FILENAME}"
    for raw_line in diff_text.splitlines():
        parts = raw_line.strip().split("\t")
        if len(parts) >= 2 and parts[0].startswith("A") and parts[1] == expected:
            return True
    return False


def sitemap_urls_from_xml(sitemap_xml: str) -> list[str]:
    """Read canonical URLs from the generated sitemap, preserving document order."""
    root = ET.fromstring(sitemap_xml)
    urls: list[str] = []
    seen: set[str] = set()
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "loc" or not element.text:
            continue
        url = element.text.strip()
        if not url.startswith(BASE_URL + "/") or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def select_submission_urls(diff_text: str, sitemap_xml: str) -> list[str]:
    """Use the sitemap for first-time bootstrap, then only changed HTML pages."""
    if is_bootstrap_diff(diff_text):
        return sitemap_urls_from_xml(sitemap_xml)
    return changed_page_urls(diff_text)


def build_payload(urls: list[str]) -> dict:
    """Build the official bulk IndexNow JSON payload."""
    return {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": list(urls),
    }


def batch_urls(urls: list[str], batch_size: int = MAX_URLS_PER_BATCH):
    """Yield IndexNow-compliant URL batches."""
    if batch_size < 1 or batch_size > MAX_URLS_PER_BATCH:
        raise ValueError("batch_size must be between 1 and 10000")
    for start in range(0, len(urls), batch_size):
        yield urls[start : start + batch_size]


def is_success_status(status: int) -> bool:
    """IndexNow accepts 200 normally and may return 202 on initial verification."""
    return status in {200, 202}
