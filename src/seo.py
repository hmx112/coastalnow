"""Search indexing policy and static SEO artifact helpers for CoastalNow."""
from __future__ import annotations

import json
import re
from html import escape

SITE_ORIGIN = "https://coastalnow.pages.dev"


def canonical_url(path: str) -> str:
    clean = (path or "").strip().lstrip("/")
    if clean in {"", "index.html"}:
        return SITE_ORIGIN + "/"
    if clean.endswith("index.html"):
        clean = clean[: -len("index.html")]
    if not clean.endswith("/") and "." not in clean.rsplit("/", 1)[-1]:
        clean += "/"
    return f"{SITE_ORIGIN}/{clean}"


def robots_directive(location: dict) -> str:
    return "index,follow" if location.get("status") == "Live NOAA" else "noindex,follow"


def breadcrumb_json_ld(items: list[tuple[str, str]]) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": canonical_url(path),
            }
            for index, (name, path) in enumerate(items, 1)
        ],
    }
    return (
        '<script type="application/ld+json">'
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


def build_sitemap(locations: dict[str, dict]) -> str:
    urls = {canonical_url("")}
    for location in locations.values():
        urls.add(canonical_url(f'tides/{location["state_slug"]}/index.html'))
        if location.get("status") == "Live NOAA":
            urls.add(canonical_url(location["page_path"]))
    rows = "\n".join(f"  <url><loc>{escape(url)}</loc></url>" for url in sorted(urls))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def build_robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_ORIGIN}/sitemap.xml\n"
    )


def location_breadcrumbs(location: dict) -> list[tuple[str, str]]:
    return [
        ("Home", ""),
        (location["state"], f'tides/{location["state_slug"]}/index.html'),
        (location["name"], location["page_path"]),
    ]


def normalize_location_html(html: str, location: dict) -> str:
    """Apply current indexing, canonical, and breadcrumb policy to a location page."""
    canonical = canonical_url(location["page_path"])
    html = re.sub(
        r'<link\s+rel=["\']canonical["\'][^>]*>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<meta\s+name=["\']robots["\'][^>]*>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<script\s+type=["\']application/ld\+json["\'][^>]*>.*?BreadcrumbList.*?</script>\s*',
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    tags = (
        f'<meta name="robots" content="{robots_directive(location)}">\n'
        f'<link rel="canonical" href="{canonical}">\n'
        + breadcrumb_json_ld(location_breadcrumbs(location))
        + "\n"
    )
    if "</head>" not in html.lower():
        raise ValueError(f'Location page has no </head>: {location.get("slug", "unknown")}')
    return re.sub(r"</head>", tags + "</head>", html, count=1, flags=re.IGNORECASE)


def normalize_preview_html(html: str, location: dict) -> str:
    """Backward-compatible Preview normalizer used by tests and migration code."""
    if location.get("status") == "Live NOAA":
        raise ValueError("normalize_preview_html requires a Preview location")
    return normalize_location_html(html, location)
