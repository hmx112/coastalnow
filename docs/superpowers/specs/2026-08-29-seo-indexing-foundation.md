# CoastalNow SEO Indexing Foundation Spec

## Goal
Make CoastalNow discoverable and safely indexable by search engines without exposing prototype/demo tide pages as search results.

## Requirements
- Production origin is `https://coastalnow.pages.dev` until a custom domain replaces it.
- Home and state directory pages are indexable and self-canonical.
- `Live NOAA` location pages are `index,follow` and self-canonical.
- `Preview` location pages are `noindex,follow` and self-canonical.
- Replace legacy `example.com` canonical URLs on Preview pages.
- Generate `public/sitemap.xml` automatically. Include the home page, state directory pages, and Live NOAA location pages. Exclude Preview location pages.
- Generate `public/robots.txt` automatically with crawl allowed and a Sitemap directive.
- Add BreadcrumbList JSON-LD to state directory and location pages.
- Directory/site rebuilds and location promotions must regenerate SEO artifacts automatically.
- Existing Live NOAA generation and all regression tests must continue to pass.
- Do not use a meta keywords tag.
