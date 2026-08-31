# Pinterest RSS current official notes

As checked on 2026-08-31 against Pinterest Business Help:

- RSS 2.x and RSS 1.x (RDF) are supported; Atom is not.
- Each item needs a link under the claimed domain.
- Pin title and description are read from item `<title>` and `<description>`.
- Pinterest can create pin images from item `<image>`, `<enclosure>`, or `<media:content>` tags.
- Feed updates can become Pins within 24 hours.
- Older feed content is processed first.
- Up to 200 Pins per day can be created from feed updates.

For CoastalNow v1, each item uses exactly one `media:content` image element to avoid exposing the same image through multiple supported image tags.
