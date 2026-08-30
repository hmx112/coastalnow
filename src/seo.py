"""Search indexing policy and static SEO artifact helpers for CoastalNow."""
from __future__ import annotations

import json
import re
from html import escape

from activities.paths import activity_page_path

SITE_ORIGIN = "https://coastalnowtides.com"


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


def activity_robots_directive(result: dict | None) -> str:
    """Index Activity pages only when current critical data has usable confidence."""
    if not result:
        return "noindex,follow"
    today = result.get("today") or {}
    confidence = today.get("confidence")
    status = today.get("status")
    if confidence in {"High", "Medium"} and status not in {"Limited", "Unavailable"}:
        return "index,follow"
    return "noindex,follow"


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


def activity_breadcrumbs(location: dict, activity_slug: str, activity_label: str) -> list[tuple[str, str]]:
    return [
        ("Home", ""),
        (location["state"], f'tides/{location["state_slug"]}/index.html'),
        (location["name"], location["page_path"]),
        (activity_label, activity_page_path(location, activity_slug)),
    ]


def activity_seo_tags(location: dict, activity_slug: str, result: dict, activity_label: str | None = None) -> str:
    label = activity_label or activity_slug.replace("-", " ").title()
    path = activity_page_path(location, activity_slug)
    return (
        f'<meta name="robots" content="{activity_robots_directive(result)}">\n'
        f'<link rel="canonical" href="{canonical_url(path)}">\n'
        + breadcrumb_json_ld(activity_breadcrumbs(location, activity_slug, label))
        + "\n"
    )


def activity_hub_seo_tags(activity_slug: str, activity_label: str | None = None) -> str:
    label = activity_label or activity_slug.replace("-", " ").title()
    path = f"{activity_slug}/index.html"
    return (
        '<meta name="robots" content="index,follow">\n'
        f'<link rel="canonical" href="{canonical_url(path)}">\n'
        + breadcrumb_json_ld([("Home", ""), (label, path)])
        + "\n"
    )


def build_sitemap(
    locations: dict[str, dict],
    activity_inventory: dict[str, dict[str, dict]] | None = None,
) -> str:
    urls = {canonical_url("")}
    for location in locations.values():
        urls.add(canonical_url(f'tides/{location["state_slug"]}/index.html'))
        if location.get("status") == "Live NOAA":
            urls.add(canonical_url(location["page_path"]))

    if activity_inventory is not None:
        for activity_slug, results in activity_inventory.items():
            urls.add(canonical_url(f"{activity_slug}/index.html"))
            for location_slug, result in results.items():
                location = locations.get(location_slug)
                if location and activity_robots_directive(result) == "index,follow":
                    urls.add(canonical_url(activity_page_path(location, activity_slug)))

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
    """Apply current title, description, indexing, canonical, and breadcrumb policy."""
    canonical = canonical_url(location["page_path"])
    title = escape(location["page_title"])
    description = escape(location["meta_description"], quote=True)

    if not re.search(r"<title[^>]*>.*?</title>", html, flags=re.IGNORECASE | re.DOTALL):
        raise ValueError(f'Location page has no title: {location.get("slug", "unknown")}')
    html = re.sub(
        r"<title[^>]*>.*?</title>",
        f"<title>{title}</title>",
        html,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = re.sub(
        r'<meta\s+name=["\']description["\'][^>]*>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )
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
        f'<meta name="description" content="{description}">\n'
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
