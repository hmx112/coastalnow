"""Search indexing policy and static SEO artifact helpers for CoastalNow."""
from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape

from activities.paths import activity_page_path
from activities.registry import ACTIVITIES, activity_enabled_for_location

SITE_ORIGIN = "https://coastalnowtides.com"
TRUST_PAGE_PATHS = (
    "about/index.html",
    "privacy/index.html",
    "contact/index.html",
)
SEARCH_CONTEXT_PATTERN = re.compile(
    r"<!-- SEARCH_CONTEXT_START -->.*?<!-- SEARCH_CONTEXT_END -->",
    re.DOTALL,
)


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
    """Keep useful generated Activity pages indexable without masking true data failure.

    Limited days remain indexable because the page still carries useful tide, wind,
    wave, weather, attribution and methodology content. A page stays noindex only
    when no Activity result exists or both Today and Tomorrow are unavailable.
    """
    if not result:
        return "noindex,follow"
    for day_key in ("today", "tomorrow"):
        day = result.get(day_key)
        if isinstance(day, dict) and day.get("status") not in {None, "", "Unavailable"}:
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
    urls = {
        canonical_url(""),
        canonical_url("methodology/index.html"),
        *(canonical_url(path) for path in TRUST_PAGE_PATHS),
    }
    for location in locations.values():
        urls.add(canonical_url(f'tides/{location["state_slug"]}/index.html'))
        if location.get("status") == "Live NOAA":
            urls.add(canonical_url(location["page_path"]))

    if activity_inventory is not None:
        for activity_slug, results in activity_inventory.items():
            activity = ACTIVITIES.get(activity_slug)
            if not activity or not activity.get("enabled"):
                continue
            urls.add(canonical_url(f"{activity_slug}/index.html"))
            for location_slug, result in results.items():
                location = locations.get(location_slug)
                if (
                    location
                    and activity_enabled_for_location(activity, location_slug)
                    and activity_robots_directive(result) == "index,follow"
                ):
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


def _format_tide_time(raw: str) -> str:
    value = datetime.strptime(raw, "%Y-%m-%d %H:%M").strftime("%I:%M %p")
    return value[1:] if value.startswith("0") else value


def _format_tide_height(value) -> str:
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def _today_tide_summary(location: dict, tide_data: dict | None) -> str:
    context = location.get("search_context") or {}
    if not context.get("today_summary") or not tide_data:
        return ""
    generated_at_local = tide_data.get("generated_at_local") or ""
    local_day = generated_at_local[:10]
    if not local_day:
        return ""
    events = [
        item
        for item in (tide_data.get("hilo") or [])
        if isinstance(item, dict) and str(item.get("t", "")).startswith(local_day)
    ]
    highs = [item for item in events if item.get("type") == "H"]
    lows = [item for item in events if item.get("type") == "L"]
    if not highs or not lows:
        return ""
    high = max(highs, key=lambda item: float(item["v"]))
    low = min(lows, key=lambda item: float(item["v"]))
    return (
        f'{location["name"]} tides today reach a predicted high of {_format_tide_height(high["v"])} ft '
        f'at {_format_tide_time(high["t"])} and a predicted low of {_format_tide_height(low["v"])} ft '
        f'at {_format_tide_time(low["t"])}, {location.get("time_label", "local time")}.'
    )


def _search_context_html(location: dict, tide_data: dict | None = None) -> str:
    context = location.get("search_context")
    if not context:
        return ""
    title = escape(context.get("title") or "Local tide context")
    paragraph_values = []
    today_summary = _today_tide_summary(location, tide_data)
    if today_summary:
        paragraph_values.append(today_summary)
    paragraph_values.extend(
        paragraph for paragraph in (context.get("paragraphs") or []) if paragraph
    )
    paragraphs = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraph_values)
    if not paragraphs:
        return ""
    related_links = context.get("related_links") or []
    related_html = ""
    if related_links:
        links = " · ".join(
            f'<a href="{escape(link.get("href", ""), quote=True)}"><strong>{escape(link.get("label", "Nearby tides"))}</strong></a>'
            for link in related_links
            if link.get("href")
        )
        if links:
            related_html = f'<p class="local-search-links">Compare nearby tides: {links}</p>'
    return (
        '<!-- SEARCH_CONTEXT_START -->'
        '<section class="section local-search-context"><article class="info-card">'
        '<p class="eyebrow">LOCAL TIDE CONTEXT</p>'
        f"<h2>{title}</h2>{paragraphs}{related_html}"
        '</article></section>'
        '<!-- SEARCH_CONTEXT_END -->'
    )


C2_TIDE_PILOT_SLUGS = {
    "malibu",
    "los-angeles",
    "oceanside",
    "miami-beach",
}
C2_TIDE_ASSET_VERSION = "20260924-hero-1"
C2_TIDE_STYLESHEET = (
    f'<link rel="stylesheet" href="/assets/malibu-c2.css?v={C2_TIDE_ASSET_VERSION}" '
    'data-coastalnow-design="tide-c2">\n'
)


def _c2_section_tabs(location: dict) -> str:
    """Render C2 navigation only for activities that are public at this location."""
    state_slug = location["state_slug"]
    slug = location["slug"]
    base = f"/tides/{state_slug}/{slug}"
    items = [
        '<a href="#overview">Overview</a>',
        '<a href="#tide-chart">Tide chart</a>',
    ]
    for activity_slug in ("fishing", "surfing"):
        activity = ACTIVITIES.get(activity_slug)
        if activity and activity_enabled_for_location(activity, slug):
            items.append(
                f'<a href="{base}/{activity_slug}/">{escape(activity["label"])}</a>'
            )
    items.append('<a href="#data">Data</a>')
    label = escape(f'{location["name"]} page sections', quote=True)
    return f'<nav class="c2-section-tabs" aria-label="{label}">' + "".join(items) + "</nav>"


def _apply_location_design_pilot(html: str, location: dict) -> str:
    """Apply the opt-in C2 visual pilot without changing shared Tide markup."""
    slug = location.get("slug")
    if slug not in C2_TIDE_PILOT_SLUGS:
        return html

    if 'data-coastalnow-design="tide-c2"' not in html:
        html = re.sub(
            r"</head>",
            C2_TIDE_STYLESHEET + "</head>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )

    body_class = f'c2-tide c2-{slug}'
    if f'class="{body_class}"' not in html:
        html = re.sub(
            r"<body>",
            f'<body class="{body_class}">',
            html,
            count=1,
            flags=re.IGNORECASE,
        )

    if 'class="c2-section-tabs"' not in html:
        hero = re.search(r'<section class="hero">.*?</section>', html, flags=re.IGNORECASE | re.DOTALL)
        if not hero:
            raise ValueError(f"{slug} C2 pilot requires the Tide hero section")
        html = html[: hero.end()] + "\n" + _c2_section_tabs(location) + html[hero.end() :]

    if 'id="overview"' not in html:
        html = re.sub(
            r'<section class="section">\s*<div class="section-head">',
            '<section class="section" id="overview"><div class="section-head">',
            html,
            count=1,
            flags=re.IGNORECASE,
        )

    if 'id="tide-chart"' not in html:
        html = html.replace(
            '<section class="section chart-card">',
            '<section class="section chart-card" id="tide-chart">',
            1,
        )
    return html


def _enrich_location_body(html: str, location: dict, tide_data: dict | None = None) -> str:
    """Keep editorial context and trust navigation stable across Tide refreshes."""
    html = re.sub(
        r'\s*<div class="ad-slot">\s*<div><span>ADVERTISEMENT</span>AdSense placement after core tide information</div>\s*</div>',
        "",
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'\s*<div class="ad-slot">\s*<div><span>ADVERTISEMENT</span>Second AdSense placement</div>\s*</div>',
        "",
        html,
        count=1,
        flags=re.IGNORECASE,
    )

    context_block = _search_context_html(location, tide_data)
    if SEARCH_CONTEXT_PATTERN.search(html):
        html = SEARCH_CONTEXT_PATTERN.sub(context_block, html, count=1)
    elif context_block:
        marker = '<section class="section lower-grid">'
        if marker in html:
            html = html.replace(marker, context_block + "\n\n  " + marker, 1)
        else:
            raise ValueError(f'Location page has no local-guide insertion point: {location.get("slug", "unknown")}')

    if "Methodology" not in html:
        footer_marker = '<div class="footer-links">'
        if footer_marker in html:
            html = html.replace(
                footer_marker,
                footer_marker + '<a href="../../../methodology/index.html">Methodology</a>',
                1,
            )
    return html


def normalize_location_html(html: str, location: dict, tide_data: dict | None = None) -> str:
    """Apply current content, title, description, indexing, canonical, and breadcrumb policy."""
    html = _enrich_location_body(html, location, tide_data)
    html = _apply_location_design_pilot(html, location)
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
