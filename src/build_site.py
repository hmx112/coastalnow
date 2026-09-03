"""Build directory, Tide, and enabled Activity pages with search metadata."""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from activities.paths import activity_data_path, activity_hub_path, activity_page_path
from activities.registry import enabled_activities, enabled_activities_for_location
from activities.rendering.attribution import (
    hub_attribution_html,
    inject_attribution,
    location_attribution_html,
)
from activities.rendering.hub_page import render_fishing_hub
from activities.rendering.links import activity_location_url
from activities.rendering.location_page import render_fishing_location
from activities.rendering.methodology_page import render_methodology_page
from activities.rendering.surfing_page import render_surfing_hub, render_surfing_location
from locations import LOCATIONS
from seo import (
    activity_hub_seo_tags,
    activity_seo_tags,
    build_robots_txt,
    build_sitemap,
    normalize_location_html,
)
from site_generator import LOGO, build_directory_pages

ROOT = Path(__file__).resolve().parents[1] / "public"
LOGO_PATTERN = re.compile(
    r'<span class="logo-mark">\s*<svg viewBox="0 0 24 24" aria-hidden="true">.*?</svg>\s*</span>',
    re.DOTALL,
)
ACTIVITY_BLOCK_PATTERN = re.compile(
    r"<!-- ACTIVITY_LINKS_START -->.*?<!-- ACTIVITY_LINKS_END -->",
    re.DOTALL,
)
ACTIVITY_NAV_PATTERN = re.compile(
    r"<!-- ACTIVITY_NAV_START -->.*?<!-- ACTIVITY_NAV_END -->",
    re.DOTALL,
)
ACTIVITY_PRIMARY_PATTERN = re.compile(
    r"<!-- ACTIVITY_PRIMARY_START -->.*?<!-- ACTIVITY_PRIMARY_END -->",
    re.DOTALL,
)
HERO_SECTION_PATTERN = re.compile(
    r'(<section class="hero"[^>]*>.*?</section>)',
    re.DOTALL,
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_brand_logo(html: str) -> str:
    normalized, count = LOGO_PATTERN.subn(LOGO, html, count=1)
    if count != 1:
        raise ValueError("Location page logo markup was not found exactly once")
    return normalized


def load_activity_inventory(public_root: Path = ROOT, *, locations: dict[str, dict] | None = None) -> dict[str, dict[str, dict]]:
    """Load generated JSON for every enabled Activity directly from the location catalog."""
    locations = LOCATIONS if locations is None else locations
    inventory: dict[str, dict[str, dict]] = {}
    for activity in enabled_activities():
        slug = activity["slug"]
        results: dict[str, dict] = {}
        for location_slug, location in locations.items():
            if not any(item["slug"] == slug for item in enabled_activities_for_location(location)):
                continue
            path = public_root / activity_data_path(location, slug)
            if not path.exists():
                continue
            result = read_json(path)
            if result.get("activity") not in {None, slug}:
                raise ValueError(f"{path}: activity mismatch")
            if result.get("location") not in {None, location_slug}:
                raise ValueError(f"{path}: location mismatch")
            results[location_slug] = result
        inventory[slug] = results
    return inventory


def _activity_link_card(location: dict, activity: dict, result: dict) -> str:
    today = result.get("today") or {}
    score = today.get("score")
    status = today.get("status") or "Unavailable"
    confidence = today.get("confidence") or "Unavailable"
    if status == "NOT RECOMMENDED":
        summary = "NOT RECOMMENDED"
    elif score is None:
        summary = status
    else:
        rating = today.get("rating") or ""
        summary = f'{float(score):g} {rating}'.strip()
    return (
        f'<a class="info-card activity-parent-card" href="{escape(activity_location_url(location, activity["slug"]))}">'
        f'<span class="state-code">{escape(activity["label"].upper())}</span>'
        f'<h3>{escape(activity["label"])} Conditions Today</h3>'
        f'<p>{escape(summary)} · Confidence: {escape(confidence)}</p>'
        f'<span class="card-arrow">Plan {escape(activity["label"].lower())} →</span></a>'
    )


def _inject_activity_nav(html: str, nav_block: str) -> str:
    """Insert/replace compact Activity links in the Tide header when that header exists."""
    if ACTIVITY_NAV_PATTERN.search(html):
        return ACTIVITY_NAV_PATTERN.sub(nav_block, html, count=1)
    if not nav_block:
        return html

    header_end = html.lower().find("</header>")
    if header_end < 0:
        return html
    header = html[:header_end]
    search_marker = '<span class="search-pill">'
    marker_index = header.rfind(search_marker)
    if marker_index >= 0:
        return html[:marker_index] + nav_block + html[marker_index:]
    nav_end = header.rfind("</nav>")
    if nav_end >= 0:
        return html[:nav_end] + nav_block + html[nav_end:]
    return html


def _primary_activity_cta(location: dict, configured: dict[str, dict], activity_results: dict[str, dict]) -> str:
    cards = []
    location_name = escape(location["name"])
    for slug, activity in configured.items():
        if not activity_results.get(slug):
            continue
        href = escape(activity_location_url(location, slug))
        if slug == "fishing":
            eyebrow = "FISHING"
            title = f"Fishing conditions for {location_name}"
            copy = "See tide, wind, wave and weather context for shore, pier and nearshore fishing."
            cta = "View fishing conditions →"
        elif slug == "surfing":
            eyebrow = "SURFING"
            title = f"Surf conditions for {location_name}"
            copy = "See wave height, period, wind, weather and tide context for general coastal surf planning."
            cta = "View surf conditions →"
        else:
            eyebrow = escape(activity["label"].upper())
            title = f'{escape(activity["label"])} conditions for {location_name}'
            copy = "See current coastal planning context for this activity."
            cta = f'View {escape(activity["label"].lower())} conditions →'
        cards.append(
            f'<a class="activity-primary-cta" href="{href}"><div class="info-card">'
            f'<p class="eyebrow">{eyebrow}</p><h2>{title}</h2><p>{copy}</p>'
            f'<p><strong>{cta}</strong></p></div></a>'
        )
    if not cards:
        return ""
    return (
        '<!-- ACTIVITY_PRIMARY_START -->'
        '<section class="section activity-primary-section"><div class="directory-grid">'
        + "".join(cards)
        + '</div></section><!-- ACTIVITY_PRIMARY_END -->'
    )
def _inject_primary_activity_cta(html: str, primary_block: str) -> str:
    if ACTIVITY_PRIMARY_PATTERN.search(html):
        return ACTIVITY_PRIMARY_PATTERN.sub(primary_block, html, count=1)
    if not primary_block:
        return html
    hero = HERO_SECTION_PATTERN.search(html)
    if not hero:
        return html
    return html[:hero.end()] + primary_block + html[hero.end():]


def inject_activity_links(html: str, location: dict, activity_results: dict[str, dict]) -> str:
    """Insert/replace Tide-to-Activity navigation and cards without changing the Tide URL."""
    cards = []
    nav_links = []
    configured = {item["slug"]: item for item in enabled_activities_for_location(location)}
    for slug, activity in configured.items():
        result = activity_results.get(slug)
        if result:
            cards.append(_activity_link_card(location, activity, result))
            nav_links.append(
                f'<a class="activity-nav-link" href="{escape(activity_location_url(location, slug))}">'
                f'{escape(activity["label"])}</a>'
            )

    nav_block = ""
    if nav_links:
        nav_block = '<!-- ACTIVITY_NAV_START -->' + "".join(nav_links) + '<!-- ACTIVITY_NAV_END -->'
        html = _inject_activity_nav(html, nav_block)
    if nav_block:
        html = html.replace(
            ".nav>a{display:none}",
            ".nav>a:not(.activity-nav-link){display:none}",
            1,
        )

    primary_block = _primary_activity_cta(location, configured, activity_results)
    html = _inject_primary_activity_cta(html, primary_block)

    block = ""
    if cards:
        block = (
            '<!-- ACTIVITY_LINKS_START -->'
            '<section class="section activity-parent-section"><div class="section-head">'
            '<div><p class="eyebrow">ACTIVITY PLANNER</p><h2>Plan coastal activities</h2></div>'
            '<p>Conditions use activity-specific rules and safety context.</p></div>'
            '<div class="directory-grid">' + "".join(cards) + '</div></section>'
            '<!-- ACTIVITY_LINKS_END -->'
        )

    if ACTIVITY_BLOCK_PATTERN.search(html):
        return ACTIVITY_BLOCK_PATTERN.sub(block, html, count=1)
    if not block:
        return html
    if re.search(r"</main>", html, flags=re.IGNORECASE):
        return re.sub(r"</main>", block + "</main>", html, count=1, flags=re.IGNORECASE)
    if re.search(r"<footer", html, flags=re.IGNORECASE):
        return re.sub(r"<footer", block + "<footer", html, count=1, flags=re.IGNORECASE)
    raise ValueError("Could not find insertion point for Activity links")


def render_methodology_output(public_root: Path) -> str:
    relative = "methodology/index.html"
    output = public_root / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_methodology_page(), encoding="utf-8")
    return relative


def render_activity_outputs(
    public_root: Path,
    locations: dict[str, dict],
    inventory: dict[str, dict[str, dict]],
) -> set[str]:
    """Render enabled Activity hubs and child pages from already-generated JSON."""
    rendered: set[str] = set()
    for activity in enabled_activities():
        slug = activity["slug"]
        results = inventory.get(slug, {})
        if slug == "fishing":
            location_renderer = render_fishing_location
            hub_renderer = render_fishing_hub
        elif slug == "surfing":
            location_renderer = render_surfing_location
            hub_renderer = render_surfing_hub
        else:
            continue

        for location_slug, result in results.items():
            location = locations.get(location_slug)
            if not location:
                continue
            snapshot_path = public_root / "data" / "conditions" / f"{location_slug}.json"
            if not snapshot_path.exists():
                raise FileNotFoundError(f"Missing Activity condition snapshot: {snapshot_path}")
            snapshot = read_json(snapshot_path)
            relative = activity_page_path(location, slug)
            output = public_root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            html = location_renderer(
                location,
                result,
                snapshot,
                head_extra=activity_seo_tags(location, slug, result, activity["label"]),
            )
            html = inject_attribution(html, location_attribution_html(location, snapshot, activity_slug=slug))
            output.write_text(html, encoding="utf-8")
            rendered.add(relative)

        hub_relative = activity_hub_path(slug)
        hub_output = public_root / hub_relative
        hub_output.parent.mkdir(parents=True, exist_ok=True)
        hub_html = hub_renderer(
            locations,
            results,
            head_extra=activity_hub_seo_tags(slug, activity["label"]),
        )
        hub_html = inject_attribution(hub_html, hub_attribution_html(activity_slug=slug))
        hub_output.write_text(hub_html, encoding="utf-8")
        rendered.add(hub_relative)
    return rendered


def main():
    inventory = load_activity_inventory(ROOT)

    for relative_path, html in build_directory_pages().items():
        output = ROOT / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print(f"Rendered {output}")

    methodology_relative = render_methodology_output(ROOT)
    print(f"Rendered {ROOT / methodology_relative}")

    rendered_activities = render_activity_outputs(ROOT, LOCATIONS, inventory)
    for relative_path in sorted(rendered_activities):
        print(f"Rendered {ROOT / relative_path}")

    for location in LOCATIONS.values():
        output = ROOT / location["page_path"]
        if not output.exists():
            raise FileNotFoundError(f"Missing location page: {output}")
        html = output.read_text(encoding="utf-8")
        location_results = {
            activity_slug: results[location["slug"]]
            for activity_slug, results in inventory.items()
            if location["slug"] in results
        }
        normalized = inject_activity_links(html, location, location_results)
        normalized = normalize_location_html(normalized, location)
        normalized = normalize_brand_logo(normalized)
        output.write_text(normalized, encoding="utf-8")
        print(f"Normalized SEO, branding and Activities {output}")

    sitemap = ROOT / "sitemap.xml"
    sitemap.write_text(build_sitemap(LOCATIONS, inventory), encoding="utf-8")
    print(f"Rendered {sitemap}")

    robots = ROOT / "robots.txt"
    robots.write_text(build_robots_txt(), encoding="utf-8")
    print(f"Rendered {robots}")


if __name__ == "__main__":
    main()
