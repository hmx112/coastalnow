# CoastalNow SEO Indexing Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic canonical, robots, sitemap, Preview noindex, and breadcrumb structured-data support that follows each location's Live NOAA/Preview status.

**Architecture:** Add a focused `src/seo.py` module that owns site origin, URL building, robots directives, sitemap/robots generation, breadcrumb JSON-LD, and legacy Preview-page head normalization. Directory and tide-page renderers consume these helpers; `build_site.py` writes SEO artifacts and normalizes Preview pages so every future promotion/rebuild updates SEO automatically.

**Tech Stack:** Python 3.12 standard library, static HTML, GitHub Actions, Cloudflare Pages.

**Spec:** `docs/superpowers/specs/2026-08-29-seo-indexing-foundation.md`

## Global Constraints
- Production origin is `https://coastalnow.pages.dev` until replaced by a custom domain.
- Live NOAA detail pages are indexable; Preview detail pages are noindex/follow.
- Preview URLs must not appear in sitemap.xml.
- No meta keywords tag.
- Existing NOAA generation behavior must remain unchanged.

---

### Task 1: SEO policy and artifact generation

**Files:**
- Create: `src/seo.py`
- Create: `src/test_seo_generation.py`

**Interfaces:**
- Produces: `SITE_ORIGIN`, `canonical_url(path)`, `robots_directive(location)`, `breadcrumb_json_ld(items)`, `build_sitemap(locations)`, `build_robots_txt()`, `normalize_preview_html(html, location)`.

- [ ] **Step 1: Write failing tests** for canonical URLs, Live/Preview robots directives, sitemap inclusion/exclusion, robots.txt, breadcrumb JSON-LD, and replacement of legacy `example.com` canonical markup.
- [ ] **Step 2: Run `python src/test_seo_generation.py`** and verify failure because `src/seo.py` does not exist.
- [ ] **Step 3: Implement `src/seo.py`** using only the Python standard library. Sitemap must contain `/`, every `/tides/<state>/`, and only Live NOAA detail URLs.
- [ ] **Step 4: Run `python src/test_seo_generation.py`** and verify all tests pass.
- [ ] **Step 5: Commit** the test and module.

### Task 2: Integrate SEO into detail and directory rendering

**Files:**
- Modify: `src/templates/tide-page.html`
- Modify: `src/generate_tides.py`
- Modify: `src/site_generator.py`
- Modify: `src/build_site.py`
- Test: `src/test_seo_generation.py`, `src/test_directory_generation.py`, `src/test_integrated_render.py`

**Interfaces:**
- Consumes: helpers from `src/seo.py`.
- Produces: canonical/robots/BreadcrumbList markup on rendered pages plus `public/sitemap.xml` and `public/robots.txt`.

- [ ] **Step 1: Extend failing integration tests** so Live detail pages require `index,follow`, Preview detail pages require `noindex,follow`, directory pages require self-canonical markup, and all Preview public pages contain no `example.com` canonical.
- [ ] **Step 2: Run integration tests** and verify they fail against current renderers.
- [ ] **Step 3: Add `ROBOTS_META`, `CANONICAL_URL`, and `BREADCRUMB_JSON_LD` template tokens** and fill them from `generate_tides.static_replacements`.
- [ ] **Step 4: Update directory `_shell` rendering** with index/follow robots, canonical, and BreadcrumbList JSON-LD.
- [ ] **Step 5: Update `build_site.py`** to write directory pages, normalize all Preview detail pages, and write `sitemap.xml`/`robots.txt`.
- [ ] **Step 6: Rebuild the site and run all SEO/directory/render tests** until green.
- [ ] **Step 7: Commit** renderer and generated-output changes.

### Task 3: Keep SEO artifacts current in automation

**Files:**
- Modify: `.github/workflows/promote-location.yml`
- Modify: `.github/workflows/update-san-diego.yml`

**Interfaces:**
- Consumes: `src/build_site.py` generated SEO artifacts.
- Produces: commits that include `public/sitemap.xml` and `public/robots.txt` after promotions and scheduled refreshes.

- [ ] **Step 1: Add regression execution for `python src/test_seo_generation.py`** to promotion and scheduled refresh workflows.
- [ ] **Step 2: Add `public/sitemap.xml` and `public/robots.txt` to workflow commit staging.**
- [ ] **Step 3: Run the complete offline regression suite:** `test_location_promotion.py`, `test_generate_tides.py`, `test_directory_generation.py`, `test_seo_generation.py`, `test_integrated_render.py`, `test_san_diego_fixture.py`.
- [ ] **Step 4: Inspect final diff** for accidental Preview indexing, legacy example.com canonicals, or CI-skip text.
- [ ] **Step 5: Create PR, verify mergeability/checks, and squash merge.**
