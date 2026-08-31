"""Submit changed CoastalNow public pages to IndexNow."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://coastalnowtides.com"
HOST = "coastalnowtides.com"
INDEXNOW_KEY = "d9841f79a4de725f16d6ed88c7807a68"
KEY_FILENAME = f"{INDEXNOW_KEY}.txt"
KEY_LOCATION = f"{BASE_URL}/{KEY_FILENAME}"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS_PER_BATCH = 10_000
ROOT = Path(__file__).resolve().parent.parent
SITEMAP_PATH = ROOT / "public" / "sitemap.xml"


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


def post_batch(urls: list[str], *, opener=urlopen, timeout: float = 20.0) -> int:
    """POST one UTF-8 JSON batch to the shared IndexNow endpoint."""
    if not urls:
        raise ValueError("IndexNow batch must contain at least one URL")
    data = json.dumps(build_payload(urls), ensure_ascii=False).encode("utf-8")
    request = Request(
        INDEXNOW_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with opener(request, timeout=timeout) as response:
        return int(response.status)


def submit_urls(
    urls: list[str],
    *,
    opener=urlopen,
    sleep=time.sleep,
    max_attempts: int = 6,
    retry_delay: float = 10.0,
) -> list[int]:
    """Submit URL batches, retrying transient key propagation/rate/server responses."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    statuses: list[int] = []
    retryable_statuses = {403, 429, 500, 502, 503, 504}

    for batch in batch_urls(urls):
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                status = post_batch(batch, opener=opener)
                if is_success_status(status):
                    statuses.append(status)
                    break
                last_error = RuntimeError(f"IndexNow returned HTTP {status}")
                retryable = status in retryable_statuses
            except HTTPError as exc:
                status = int(exc.code)
                last_error = exc
                retryable = status in retryable_statuses
            except URLError as exc:
                last_error = exc
                retryable = True

            if not retryable or attempt + 1 >= max_attempts:
                raise RuntimeError(f"IndexNow submission failed after {attempt + 1} attempt(s): {last_error}") from last_error
            sleep(retry_delay)
        else:
            raise RuntimeError("IndexNow submission exhausted retries")

    return statuses


def git_diff_name_status(before: str, after: str) -> str:
    """Read changed public paths for one main-branch push."""
    result = subprocess.run(
        ["git", "diff", "--name-status", before, after, "--", "public"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def load_sitemap() -> str:
    return SITEMAP_PATH.read_text(encoding="utf-8")


def run_submission(
    before: str,
    after: str,
    *,
    diff_loader=git_diff_name_status,
    sitemap_loader=load_sitemap,
    submitter=submit_urls,
) -> int:
    """Select and submit URLs for a GitHub main push; return URL count."""
    diff_text = diff_loader(before, after)
    sitemap_xml = sitemap_loader() if is_bootstrap_diff(diff_text) else ""
    urls = select_submission_urls(diff_text, sitemap_xml)
    if not urls:
        print("IndexNow: no changed public HTML pages to submit.")
        return 0
    statuses = submitter(urls)
    print(f"IndexNow: submitted {len(urls)} URL(s) in {len(statuses)} batch(es); statuses={statuses}")
    return len(urls)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit changed CoastalNow public pages to IndexNow")
    parser.add_argument("--before", required=True, help="Git commit before the main push")
    parser.add_argument("--after", required=True, help="Git commit after the main push")
    args = parser.parse_args(argv)
    run_submission(args.before, args.after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
