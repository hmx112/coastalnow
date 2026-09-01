# CoastalNow Pinterest Pin v2 — Implementation Specification

Status: Approved design direction
Scope: Replace the current decorative Pinterest pin visuals with information-first Tide and Fishing templates while preserving the existing RSS/release architecture.

## 1. Goals

The Pinterest pin must explain what CoastalNow provides at a glance, even when viewed small in the Pinterest feed.

The v2 design must:
- use CoastalNow site branding consistently;
- communicate concrete site features rather than decorative imagery;
- remain evergreen after publication;
- avoid live values that will become stale;
- keep the existing Pinterest RSS destinations and release cadence unchanged.

## 2. Files / Components

Primary implementation target:
- `src/pinterest/render.py`

Expected supporting tests:
- existing Pinterest renderer/generator tests;
- add/update renderer-specific tests as needed.

Do not change unless required by tests:
- `src/generate_pinterest.py`
- `src/pinterest/rss.py`
- `src/pinterest/schedule.py`
- `src/data/pinterest.json`

The current schedule remains `locations_per_day: 1`. When Fishing is enabled, each released location produces two pins: one Tide pin and one Fishing pin.

## 3. Canvas

- Output: PNG
- Dimensions: exactly `1000 × 1500`
- Orientation: vertical, 2:3
- Renderer: deterministic Pillow-based rendering
- No AI-generated per-location imagery in production
- No external network dependency during rendering

## 4. Brand Lock

### 4.1 Logo

Pinterest v2 must visually match the CoastalNow site header logo:
- teal rounded-square mark;
- three white horizontal wave strokes;
- `CoastalNow` wordmark in dark navy;
- no alternate circular/sun/arc logo;
- no Fishing-specific logo.

The renderer must use one shared logo drawing helper for both Tide and Fishing templates.

Recommended helper:
- `_draw_coastalnow_brand(draw, x, y, ...)`

The mark should match the site visual language: teal/seafoam rounded square with white three-wave symbol. The same helper must be used everywhere Pinterest branding appears.

### 4.2 Palette

Use the existing CoastalNow visual family:
- background: off-white / very pale aqua;
- primary text: deep navy;
- primary accent: teal;
- secondary accent: seafoam;
- optional light aqua panel fills;
- small warm accent only when useful, not as a dominant element.

Do not introduce unrelated brand colors.

### 4.3 Typography

- strong sans-serif hierarchy;
- city name is the largest location element;
- headline is highly readable at Pinterest feed size;
- feature-card labels must remain readable on mobile;
- use repository/system fonts only;
- do not commit font files.

## 5. Evergreen Content Rule

Production pin images must not include values that can become incorrect after publication.

### Allowed numeric text
- `0–100 Fishing Score`
- `7-Day Tide Forecast`
- `Best 3-hour fishing window`

These describe product structure, not current conditions.

### Prohibited dynamic values
Do not render:
- current Fishing Score value (e.g. `72`);
- current tide height;
- current high/low time;
- current wind speed/direction value;
- current wave height/period value;
- current temperature;
- precipitation percentage;
- dates/day labels;
- alert status;
- current recommended time window;
- countdowns such as `in 2h 18m`.

RSS destinations continue to send the user to the live CoastalNow page where current values are shown.

## 6. Fishing Pin Template

### 6.1 Required text hierarchy

Top brand row:
- CoastalNow site-style mark + `CoastalNow`

Location:
- `{CITY}` uppercase, visually dominant
- `{STATE}` uppercase, secondary

Main headline:
- `FISHING CONDITIONS`
- `& BEST TIMES`

Supporting line:
- `For shore, pier and nearshore fishing.`

### 6.2 Feature grid

Use six clean information cards in a 3 × 2 grid.

Card 1:
- label: `Live 0–100 Fishing Score`
- supporting copy: `See how conditions rate for fishing`
- icon: gauge / score indicator

Card 2:
- label: `Tide`
- supporting copy: `Tide movement and timing`
- icon: simple tide/wave symbol

Card 3:
- label: `Wind`
- supporting copy: `Wind speed and direction`
- icon: wind lines

Card 4:
- label: `Waves`
- supporting copy: `Wave height and period`
- icon: wave

Card 5:
- label: `Weather`
- supporting copy: `Sky, rain chance and more`
- icon: cloud/sun

Card 6:
- label: `Best 3-hour fishing window`
- supporting copy: `Top window based on today’s conditions`
- icon: clock

The cards describe available information; they must not display current measurements.

### 6.3 CTA

Large lower CTA band/button:
- `See today’s fishing conditions →`

Footer line:
- `Live tide, wind & wave context`

### 6.4 Fishing visual restrictions

Remove from the current template:
- decorative layered wave polygons that resemble a graph;
- isolated fishing-hook graphic as the main storytelling element;
- large empty decorative zones with no information purpose.

A subtle coastal/photo-like visual is optional only if deterministic and legally safe; production v2 should default to vector/graphic accents because the existing renderer has no external image dependency.

## 7. Tide Pin Template

### 7.1 Required text hierarchy

Top brand row:
- CoastalNow site-style mark + `CoastalNow`

Location:
- `{CITY}` uppercase, visually dominant
- `{STATE}` uppercase, secondary

Main headline:
- `TIDE TIMES &`
- `TIDE CHART`

Supporting line:
- `Fast local tide info for planning by the water.`

### 7.2 Feature grid

Use four clean feature cards in a 2 × 2 grid.

Card 1:
- label: `High & Low Tide Times`
- supporting copy: `Know when tides rise and fall.`
- icon: up/down tide arrows with wave

Card 2:
- label: `7-Day Tide Forecast`
- supporting copy: `Plan ahead with a weekly outlook.`
- icon: calendar

Card 3:
- label: `Live NOAA Tide Data`
- supporting copy: `Reliable source data for local tides.`
- icon: generic data/database/check symbol
- IMPORTANT: text may say NOAA; do not draw or imitate the NOAA logo.

Card 4:
- label: `Today’s Tide Chart`
- supporting copy: `See the tide pattern at a glance.`
- icon: simple schematic curve icon

The Tide Chart icon must be clearly an icon/schematic, not a graph that could be interpreted as today’s actual measured/predicted curve.

### 7.3 Value strip

A narrow four-item benefits strip may be used below the cards:
- `Local Focus`
- `Accurate NOAA Data`
- `Real-time Updates`
- `Clean & Clear`

Use simple generic icons. Do not use official agency logos.

### 7.4 CTA

Large lower CTA band/button:
- `See today’s tide times →`

Footer line:
- `Your go-to source for coastal conditions.`

## 8. Layout Geometry Guidance

The exact pixel values may be tuned during implementation, but keep this hierarchy stable:

1. Brand row: top ~8–10% of canvas
2. City/state: next ~15–18%
3. Main topic headline + supporting line: next ~15–18%
4. Feature-card area: largest central section, roughly ~38–45%
5. CTA + footer: final ~12–16%

Minimum safe margins:
- left/right: ~60 px or more
- top: ~45 px or more
- bottom: ~35 px or more

City names with long widths must use fit-to-width font sizing; never crop or overflow.

## 9. Renderer Structure Recommendation

Keep `render_pin(item, kind, output)` as the public renderer entry point.

Refactor internal helpers so visual rules are explicit and reusable:

- `_draw_coastalnow_brand(...)`
- `_draw_location_header(...)`
- `_draw_wrapped_text(...)`
- `_draw_feature_card(...)`
- `_draw_icon_score(...)`
- `_draw_icon_tide(...)`
- `_draw_icon_wind(...)`
- `_draw_icon_waves(...)`
- `_draw_icon_weather(...)`
- `_draw_icon_clock(...)`
- `_draw_icon_calendar(...)`
- `_draw_icon_data(...)`
- `_draw_cta(...)`
- `_render_fishing_pin(...)`
- `_render_tide_pin(...)`

`render_pin()` should dispatch to the Tide or Fishing template, then save the PNG.

Avoid duplicating brand, CTA, typography, and card logic between templates.

## 10. Current Release Cadence — Do Not Change

Keep:
- `locations_per_day: 1`
- one new location released per UTC release date

With Fishing enabled:
- Tide RSS receives one new Tide item for the released location;
- Fishing RSS receives one new Fishing item for the released location;
- total expected output is normally 2 new pins per day.

Do not change release order or RSS GUIDs as part of the visual redesign.

## 11. Existing Published Pins

Do not automatically create duplicate RSS items solely because the visual template changed.

For already released locations, implementation must decide explicitly between:

Preferred initial migration:
- regenerate the existing image file at the same URL/path;
- retain existing RSS GUID/destination;
- do not create a second duplicate pin entry.

Pinterest may cache the first image, so visual replacement of an already-published pin is not guaranteed. The primary goal is that all future location releases use v2.

If a deliberate republishing strategy is later desired, treat it as a separate feature with separate GUID/version policy.

## 12. Testing Requirements

### Renderer tests

For both Tide and Fishing:
- output exists;
- output is exactly `1000 × 1500`;
- deterministic render: same input => byte-identical output where environment/font is identical;
- correct city/state text is present in renderer metadata/text model;
- unsupported kind raises error.

### Evergreen-content regression

Generated pin text/data must not contain dynamic current values or date strings.

Test prohibited examples/patterns such as:
- date formats;
- mph / kt values;
- `ft` measurement values generated from live data;
- `%` precipitation values;
- actual Fishing recommendation score values.

Allowed generic structure text must remain permitted:
- `0–100`
- `7-Day`
- `3-hour`

### Brand regression

Add a testable brand helper/constant so both templates are guaranteed to use the same CoastalNow mark and wordmark logic.

### RSS / generator regressions

All existing Pinterest RSS and scheduling tests must remain green.

## 13. Acceptance Criteria

Implementation is complete only when all are true:

1. San Diego Fishing sample visibly matches the approved information-first direction.
2. San Diego Tide sample visibly matches the approved information-first direction.
3. CoastalNow logo matches the site’s teal rounded-square / three-white-wave branding.
4. No fake data graph appears.
5. No stale live values appear in either image.
6. Fishing exposes the six agreed feature blocks.
7. Tide exposes the four agreed feature blocks.
8. CTA is prominent and readable at feed size.
9. 1000×1500 output is preserved.
10. One-location-per-day release logic is unchanged.
11. Tide + Fishing continue to produce two feed items per released Fishing-enabled location.
12. Existing RSS URLs, destinations, and GUID policy remain unchanged.
13. Full repository regression suite passes.

## 14. Out of Scope for v2

Do not add during this redesign:
- live data snapshots in pin images;
- per-day current score graphics;
- dynamic tide-curve plotting from NOAA data;
- AI-generated location photography;
- Pinterest API direct posting;
- new boards;
- Surfing/Swimming pin templates;
- changed RSS schedule;
- duplicate creative variants per location.

Those may be separate future versions after v2 performance is measured.
