/**
 * Oneul Bada — isolated Cloudflare Worker experiment.
 * Scheduled collection of KHOA's 7-day Korean tidal forecasts.
 * No API key is sent to the browser. Existing CoastalNow is unchanged.
 */
const STATIONS = Object.freeze({
  incheon: { id: "DT_0001", name: "인천" },
  busan: { id: "DT_0005", name: "부산" },
  jeju: { id: "DT_0004", name: "제주" },
});
const SOURCE = "https://apis.data.go.kr/1192136/";
const ROUTES = {
  high_low: "tideFcstHghLw/GetTideFcstHghLwApiService",
  series: "tideFcstTime/GetTideFcstTimeApiService",
};
const HEIGHT_FIELDS = { high_low: "predcTdlvVl", series: "tdlvHgt" };
const CACHE_KEY_PREFIX = "tides:v1:";
const DAY_MS = 86400000;
const HEADERS = { "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*" };

export function koreaDay(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const field = name => parts.find(part => part.type === name)?.value;
  return field("year") + "-" + field("month") + "-" + field("day");
}

export function addDays(ymd, days) {
  const d = new Date(ymd + "T00:00:00Z");
  if (!Number.isFinite(d.getTime())) throw new Error("Invalid forecast date");
  return new Date(d.getTime() + days * DAY_MS).toISOString().slice(0, 10);
}

function decodePortalKey(key) {
  if (!key) throw new Error("Missing KHOA service credentials");
  try { return decodeURIComponent(key.trim()); } catch { return key.trim(); }
}

async function fetchProvider(kind, stationId, day, key, fetcher = fetch) {
  const qs = new URLSearchParams({
    serviceKey: decodePortalKey(key),
    obsCode: stationId,
    reqDate: day.replaceAll("-", ""),
    type: "json",
    numOfRows: "300",
  });
  if (kind === "series") qs.set("min", "30");
  const url = SOURCE + ROUTES[kind] + "?" + qs.toString();
  let response;
  try {
    response = await fetcher(url, { signal: AbortSignal.timeout(12000) });
  } catch {
    throw new Error("KHOA connection failed");
  }
  if (!response.ok) throw new Error("KHOA request returned HTTP " + response.status);
  try { return await response.json(); } catch { throw new Error("KHOA returned invalid JSON"); }
}

export function normalize(kind, payload, day) {
  const root = payload?.response ?? payload;
  if (!root || typeof root !== "object") throw new Error("Invalid provider response");
  const code = String(root.header?.resultCode ?? "");
  if (!["0", "00", "200"].includes(code)) throw new Error("KHOA returned unsuccessful status");
  const raw = root.body?.items?.item ?? root.body?.items;
  const rows = Array.isArray(raw) ? raw : (raw && typeof raw === "object" ? [raw] : []);
  if (!rows.length) throw new Error("No tide prediction records");
  const field = HEIGHT_FIELDS[kind];
  const out = rows.map(row => {
    if (!row || typeof row !== "object") throw new Error("Invalid tide prediction record");
    const dateStr = String(row.predcDt ?? "");
    const match = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})/.exec(dateStr);
    if (!match || match[1] !== day) throw new Error("Unexpected prediction date");
    const hour = Number(match[2]), minute = Number(match[3]);
    if (hour > 23 || minute > 59) throw new Error("Invalid prediction time");
    const value = Number(row[field]);
    if (row[field] === undefined || !Number.isFinite(value) || value < -500 || value > 2000)
      throw new Error("Missing or invalid tide height for " + kind);
    const event = { t: day + " " + match[2] + ":" + match[3], v: value };
    if (kind === "high_low") {
      const extreme = Number(row.extrSe);
      if (![1, 2, 3, 4].includes(extreme)) throw new Error("Invalid high/low code");
      event.type = [1, 3].includes(extreme) ? "H" : "L";
    }
    return event;
  }).sort((a,b)=> a.t.localeCompare(b.t));
  if (new Set(out.map(x => x.t)).size !== out.length) throw new Error("Duplicate prediction times");
  if (kind === "high_low" && !(out.some(x => x.type === "H") && out.some(x => x.type === "L")))
    throw new Error("High and low events not both present");
  if (kind === "series") {
    if (out.length !== 48 || out[0].t.slice(-5) !== "00:00" || out[47].t.slice(-5) !== "23:30")
      throw new Error("Incomplete 30-minute series");
    for (let i = 0; i < 48; i++) {
      const expected = String(Math.floor(i/2)).padStart(2,"0") + ":" + (i%2 ? "30":"00");
      if (out[i].t.slice(-5) !== expected) throw new Error("Gap in 30-minute series");
    }
  }
  return out;
}

export async function collectStation(slug, today, env, fetcher = fetch) {
  const station = STATIONS[slug];
  if (!station) throw new Error("Unknown station");
  const highKey = env.KHOA_HIGH_LOW_KEY || env.KHOA_SERVICE_KEY;
  const seriesKey = env.KHOA_SERIES_KEY || highKey;
  if (!highKey || !seriesKey) throw new Error("Missing KHOA service credentials");
  const days = [];
  for (let i = 0; i < 7; i++) {
    const day = addDays(today, i);
    const high = await fetchProvider("high_low", station.id, day, highKey, fetcher);
    const series = await fetchProvider("series", station.id, day, seriesKey, fetcher);
    days.push({
      date: day,
      hilo: normalize("high_low", high, day),
      curve: normalize("series", series, day),
    });
  }
  return {
    schema_version: 1,
    mode: "live",
    source: "KHOA / public data portal",
    attribution: "국립해양조사원 조석예보",
    station: { id: station.id, name: station.name, timezone: "Asia/Seoul" },
    units: "cm",
    datum: "Provider reference; do not interpret as actual water depth",
    date_range: { start: today, end: addDays(today, 6) },
    generated_at_utc: new Date().toISOString(),
    days,
  };
}

export function isFresh(bundle, today) {
  if (!bundle || bundle.schema_version !== 1 || !Array.isArray(bundle.days) ||
      bundle.days.length !== 7 || bundle.units !== "cm") return false;
  if (bundle.date_range?.start !== today || bundle.date_range?.end !== addDays(today, 6)) return false;
  for (let i = 0; i < 7; i++) {
    const d = bundle.days[i];
    if (d?.date !== addDays(today, i) || !Array.isArray(d.hilo) ||
        !Array.isArray(d.curve) || !d.hilo.length || d.curve.length !== 48) return false;
  }
  return true;
}

function reply(data, status = 200, cacheSeconds = 0) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...HEADERS,
      "cache-control": cacheSeconds ? "public, max-age=" + cacheSeconds : "no-store",
      "x-content-type-options": "nosniff",
    },
  });
}

export async function refreshAll(env, now = new Date(), fetcher = fetch) {
  if (!env.TIDES_KV) throw new Error("Missing TIDES_KV binding");
  const today = koreaDay(now);
  // Three concurrent station collectors, each making 14 sequential provider calls.
  const slugs = Object.keys(STATIONS);
  const results = await Promise.allSettled(slugs.map(async slug => {
    const fresh = await collectStation(slug, today, env, fetcher);
    if (!isFresh(fresh, today)) throw new Error("Incomplete station forecast");
    // Only overwrite the verified, complete station bundle.
    await env.TIDES_KV.put(CACHE_KEY_PREFIX + slug, JSON.stringify(fresh));
    return slug;
  }));
  const passed = [], failed = [];
  results.forEach((result, i) => {
    if (result.status === "fulfilled") passed.push(slugs[i]);
    else failed.push(slugs[i]);
  });
  // Never print keys, request URLs or raw upstream responses.
  console.log("KHOA refresh " + today + ": passed=" + passed.join(",") + "; failed=" + failed.join(","));
  if (failed.length) throw new Error("Some KHOA stations failed to refresh: " + failed.join(","));
  return passed;
}

export async function handleRequest(request, env, now = new Date()) {
  if (request.method !== "GET") return reply({error:"Method not allowed"}, 405);
  const url = new URL(request.url);
  if (url.pathname === "/health") {
    return reply({ service:"oneul-bada", status:"up", time_utc:now.toISOString() });
  }
  if (url.pathname !== "/api/tides") return reply({error:"Not found"}, 404);
  const slug = url.searchParams.get("station") || "incheon";
  if (!Object.hasOwn(STATIONS, slug)) return reply({error:"Unknown station"}, 400);
  if (!env.TIDES_KV) return reply({error:"Cache not configured"}, 503);
  let bundle;
  try { bundle = await env.TIDES_KV.get(CACHE_KEY_PREFIX + slug, "json"); }
  catch { return reply({error:"Cache unavailable"}, 503); }
  const today = koreaDay(now);
  if (!isFresh(bundle, today)) return reply({
    error:"Forecast temporarily unavailable",
    station:slug,
    reason:"not_fresh",
  }, 503);
  return reply(bundle, 200, 300);
}

export default {
  fetch(request, env) { return handleRequest(request, env); },
  async scheduled(_controller, env) { await refreshAll(env); },
};
