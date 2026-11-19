/** Data-only domain helpers: no UI, no SDK, no provider secrets. */
import CATALOG from '../../stations.json' with { type: 'json' };

export const STATIONS = Object.freeze(Object.fromEntries(CATALOG.map(row => [row.slug,
  { id: row.id, name: row.name, region: row.region }
])));
export const STATION_SLUGS = CATALOG.map(row => row.slug);
export const REGIONS = Object.freeze(['서해', '남해', '동해', '제주']);
export const STATION_GROUPS = Object.freeze(REGIONS.map(region => ({
  name: region,
  stations: CATALOG.filter(row => row.region === region),
})));

export function koreaDate(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now);
  const value = (name) => parts.find((p) => p.type === name)?.value;
  return `${value('year')}-${value('month')}-${value('day')}`;
}
export function shiftDay(day, offset) {
  const time = Date.parse(`${day}T00:00:00Z`);
  if (!Number.isFinite(time)) throw new Error('Invalid date');
  return new Date(time + offset * 86400000).toISOString().slice(0, 10);
}
export const asTime = (dateTime) => typeof dateTime === 'string' && /\d{2}:\d{2}$/.test(dateTime) ? dateTime.slice(-5) : '—';
export const asHeight = (value) => Number.isFinite(Number(value)) ? `${Number(value).toLocaleString('ko-KR', { maximumFractionDigits: 1 })} cm` : '—';
export function isValidBundle(bundle, slug, today = koreaDate()) {
  if (!Object.hasOwn(STATIONS, slug) || !bundle || bundle.schema_version !== 1 || bundle.mode !== 'live') return false;
  if (bundle.station?.id !== STATIONS[slug].id || bundle.units !== 'cm') return false;
  const start = bundle.date_range?.start;
  if (typeof start !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(start)) return false;
  // A 7-day prediction collected on an earlier day is still usable while
  // today's date is included. Do not require its start date to equal today.
  if (bundle.date_range?.end !== shiftDay(start, 6)) return false;
  if (today < start || today > bundle.date_range.end) return false;
  if (!Array.isArray(bundle.days) || bundle.days.length !== 7 || !bundle.generated_at_utc) return false;
  if (!Number.isFinite(Date.parse(bundle.generated_at_utc))) return false;
  return bundle.days.every((item, i) => {
    const day = shiftDay(start, i);
    if (item?.date !== day || !Array.isArray(item.hilo) || !Array.isArray(item.curve)) return false;
    if (item.hilo.length < 2 || item.curve.length !== 48) return false;
    const validRow = (row) => /^\d{4}-\d\d-\d\d \d\d:\d\d$/.test(row?.t) && row.t.startsWith(day) &&
       Number.isFinite(row?.v) && row.v >= -500 && row.v <= 2000;
    if (!item.hilo.every(row => validRow(row) && ['H', 'L'].includes(row.type))) return false;
    if (!item.hilo.some(row => row.type === 'H') || !item.hilo.some(row => row.type === 'L')) return false;
    if (!item.curve.every((row, j) => validRow(row) && row.t.endsWith(`${String(Math.floor(j/2)).padStart(2, '0')}:${j % 2 ? '30' : '00'}`))) return false;
    return true;
  });
}
/** Show only dates remaining in the verified forecast window; never show past tabs. */
export function remainingForecastDays(bundle, today = koreaDate()) {
  return Array.isArray(bundle?.days) ? bundle.days.filter(day => day.date >= today) : [];
}

export function nextTide(bundle, dayIndex, now = new Date()) {
  const day = bundle?.days?.[dayIndex];
  if (!day) return null;
  const events = [...day.hilo].sort((a,b) => a.t.localeCompare(b.t));
  if (dayIndex > 0) return events[0] || null;
  const upcoming = events.find((x) => new Date(x.t.replace(' ', 'T') + '+09:00') > now);
  if (upcoming) return upcoming;
  // Never show a past tide as an upcoming event. Use tomorrow if present.
  return bundle.days[1]?.hilo?.slice().sort((a,b) => a.t.localeCompare(b.t))[0] || null;
}
export function plotSeries(rows, width = 332, height = 170) {
  if (!Array.isArray(rows) || rows.length !== 48 || rows.some(row => !Number.isFinite(row?.v))) return null;
  let min = Math.min(...rows.map(row => row.v));
  let max = Math.max(...rows.map(row => row.v));
  if (min === max) { min -= 1; max += 1; }
  const spread = max - min;
  min -= spread * .12; max += spread * .12;
  const coords = rows.map((row,i) => ({
    x: 14 + i * (width - 28) / 47,
    y: 14 + (max - row.v) * (height - 32) / (max - min),
  }));
  return {
    line: coords.map((p,i) => `${i ? 'L' : 'M'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' '),
    fill: coords.map((p,i) => `${i ? 'L' : 'M'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ') +
      ` L ${coords.at(-1).x.toFixed(2)} ${height} L ${coords[0].x.toFixed(2)} ${height} Z`,
    minimum: Math.min(...rows.map(row => row.v)),
    maximum: Math.max(...rows.map(row => row.v)),
  };
}
export function displayDate(day) {
  const d = new Date(`${day}T00:00:00Z`);
  const weekdays = ['일','월','화','수','목','금','토'];
  return `${Number(day.slice(5, 7))}월 ${Number(day.slice(8))}일 (${weekdays[d.getUTCDay()]})`;
}
