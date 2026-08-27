# San Diego NOAA integration notes

## Official station
- NOAA/NOS/CO-OPS: `9410170`
- Station name: San Diego, CA
- Coordinates: 32.71419, -117.17358
- Tide datum: MLLW
- Display units: feet
- NOAA API time mode: LST/LDT
- Application timezone: America/Los_Angeles

## API requests

Seven-day high/low predictions:
- product: `predictions`
- interval: `hilo`
- datum: `MLLW`
- time_zone: `lst_ldt`
- units: `english`

Current direction and chart:
- product: `predictions`
- interval: `30`
- date range: today through tomorrow

Two days of interval data are requested so the rising/falling calculation can still be bracketed near midnight.

## Calculated fields

The renderer calculates rather than stores these UI values:
- `High tide in 2h 18m`
- `Low tide in ...`
- `Tide is rising now ↑`
- `Tide is falling now ↓`
- current-day SVG chart coordinates
- high/low chart labels
- desktop 7-day rows
- mobile 3-day initial view + remaining four-day expansion

## Cache policy

A failed request never falls back to generated values. A cached NOAA dataset is reused only when it still covers the current San Diego date and was generated within 30 hours. Otherwise tide values are withheld.
