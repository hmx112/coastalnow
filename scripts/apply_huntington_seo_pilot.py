from pathlib import Path

GENERATOR = Path("src/generate_tides.py")
TEMPLATE = Path("src/templates/tide-page.html")
PILOT = "huntington-beach"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_generator() -> None:
    text = GENERATOR.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"\n',
        'API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"\nHUNTINGTON_SEO_PILOT = "huntington-beach"\n',
        "pilot constant",
    )
    anchor = '''def tide_direction(data: dict, now: datetime) -> str | None:\n'''
    helpers = '''def next_tide_event(data: dict, now: datetime):\n    tz = data_tz(data)\n    events = []\n    for event in data.get("hilo", []):\n        dt = parse_noaa_dt(event["t"], tz)\n        if dt >= now:\n            events.append((dt, event))\n    return min(events, key=lambda x: x[0]) if events else None\n\n\ndef render_tide_answer(location: dict, data: dict, now: datetime) -> str:\n    if location.get("slug") != HUNTINGTON_SEO_PILOT:\n        return ""\n    next_tide = next_tide_event(data, now)\n    high = next_event(data, "H", now)\n    low = next_event(data, "L", now)\n    today = now.astimezone(data_tz(data)).date()\n    events = grouped_hilo(data)[today]["all"]\n    values = [float(event["v"]) for event in events]\n    range_text = f"{max(values) - min(values):.1f} ft" if len(values) >= 2 else "Unavailable"\n\n    def stat(label: str, event) -> str:\n        value = fmt_time(event[0]) if event else "Unavailable"\n        return f'<div><span>{label}</span><strong>{value}</strong></div>'\n\n    if next_tide:\n        dt, raw = next_tide\n        kind = "High" if raw["type"] == "H" else "Low"\n        arrow = "↑" if raw["type"] == "H" else "↓"\n        primary = (\n            f'<div class="tide-answer-main"><p class="eyebrow">NEXT TIDE</p>'\n            f'<strong class="tide-answer-kind">{arrow} {kind} tide</strong>'\n            f'<div class="tide-answer-time">{fmt_time(dt)}</div>'\n            f'<div class="tide-answer-height">{fmt_height(float(raw["v"]))}</div>'\n            f'<small>{countdown(dt, now, kind)}</small></div>'\n        )\n    else:\n        primary = (\n            '<div class="tide-answer-main"><p class="eyebrow">NEXT TIDE</p>'\n            '<strong class="tide-answer-kind">Next tide unavailable</strong></div>'\n        )\n    stats = (\n        '<div class="tide-answer-stats">'\n        + stat("Next high", high)\n        + stat("Next low", low)\n        + f'<div><span>Today\\'s range</span><strong>{range_text}</strong></div>'\n        + '</div>'\n    )\n    return f'<article class="tide-answer">{primary}{stats}</article>'\n\n\n'''
    text = replace_once(text, anchor, helpers + anchor, "answer helpers")
    text = replace_once(
        text,
        '        "TIDE_CARDS": \'<div class="tide-grid"><div class="unavailable-card">Next high tide unavailable.</div><div class="unavailable-card">Next low tide unavailable.</div></div>\',\n',
        '        "TIDE_ANSWER": "",\n        "TIDE_CARDS": \'<div class="tide-grid"><div class="unavailable-card">Next high tide unavailable.</div><div class="unavailable-card">Next low tide unavailable.</div></div>\',\n',
        "unavailable answer",
    )
    old_static = '''def static_replacements(location: dict) -> dict:\n    return {\n'''
    new_static = '''def static_replacements(location: dict) -> dict:\n    activity_cta = primary_activity_cta(location)\n    is_huntington_pilot = location.get("slug") == HUNTINGTON_SEO_PILOT\n    return {\n'''
    text = replace_once(text, old_static, new_static, "static replacements prelude")
    text = replace_once(
        text,
        '        "ACTIVITY_PRIMARY_CTA": primary_activity_cta(location),\n',
        '        "ACTIVITY_PRIMARY_PRE_TIDES": "" if is_huntington_pilot else activity_cta,\n        "ACTIVITY_PRIMARY_POST_TIDES": activity_cta if is_huntington_pilot else "",\n',
        "activity placement",
    )
    text = replace_once(
        text,
        '            "UPDATED_TEXT": f"Updated {fmt_time(generated)} {generated.tzname() or \'local time\'}",\n            "TIDE_CARDS": render_tide_cards(data, now),\n',
        '            "UPDATED_TEXT": f"Updated {fmt_time(generated)} {generated.tzname() or \'local time\'}",\n            "TIDE_ANSWER": render_tide_answer(location, data, now),\n            "TIDE_CARDS": render_tide_cards(data, now),\n',
        "dynamic answer",
    )
    GENERATOR.write_text(text, encoding="utf-8")


def patch_template() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "{{ACTIVITY_PRIMARY_CTA}}",
        "{{ACTIVITY_PRIMARY_PRE_TIDES}}",
        "pre-tide activity token",
    )
    text = replace_once(
        text,
        "    {{TIDE_CARDS}}\n",
        "    {{TIDE_ANSWER}}\n\n    {{TIDE_CARDS}}\n",
        "answer token",
    )
    text = replace_once(
        text,
        "    {{STATUS_STRIP}}\n  </section>\n\n  <section class=\"section chart-card\">",
        "    {{STATUS_STRIP}}\n  </section>\n\n  {{ACTIVITY_PRIMARY_POST_TIDES}}\n\n  <section class=\"section chart-card\">",
        "post-tide activity token",
    )
    css_anchor = '''.status-strip{\n'''
    css = '''.tide-answer{\n  margin:0 0 16px;border:1px solid #bcdfe1;border-radius:24px;padding:24px;\n  background:linear-gradient(135deg,#f7ffff,#e8f7f7);box-shadow:0 12px 34px rgba(24,60,70,.055);\n  display:grid;grid-template-columns:minmax(220px,.8fr) 1.2fr;gap:24px;align-items:center\n}\n.tide-answer-main{min-width:0}.tide-answer-main .eyebrow{margin-bottom:6px}\n.tide-answer-kind{display:block;font-size:1rem;color:#315d62}\n.tide-answer-time{font-size:clamp(2.2rem,5vw,3.7rem);font-weight:850;line-height:.98;letter-spacing:-.055em;margin-top:8px}\n.tide-answer-height{font-weight:750;color:#526d76;margin-top:6px}.tide-answer-main small{display:block;color:#73878f;margin-top:4px}\n.tide-answer-stats{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid #d4e8e8;border-radius:18px;background:rgba(255,255,255,.78);overflow:hidden}\n.tide-answer-stats>div{padding:16px;min-width:0}.tide-answer-stats>div+div{border-left:1px solid #dce9e9}\n.tide-answer-stats span{display:block;color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;font-weight:800}\n.tide-answer-stats strong{display:block;margin-top:5px;font-size:.98rem}\n\n'''
    text = replace_once(text, css_anchor, css + css_anchor, "answer styles")
    text = replace_once(
        text,
        "  .tide-grid{grid-template-columns:1fr}\n",
        "  .tide-answer{grid-template-columns:1fr}\n  .tide-grid{grid-template-columns:1fr}\n",
        "tablet answer style",
    )
    text = replace_once(
        text,
        "  .tide-card{border-radius:20px;padding:21px;min-height:170px}\n",
        "  .tide-answer{border-radius:20px;padding:19px}\n  .tide-answer-stats{grid-template-columns:1fr}\n  .tide-answer-stats>div+div{border-left:0;border-top:1px solid #dce9e9}\n  .tide-card{border-radius:20px;padding:21px;min-height:170px}\n",
        "mobile answer style",
    )
    TEMPLATE.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_generator()
    patch_template()
