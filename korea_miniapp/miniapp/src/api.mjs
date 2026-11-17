import { isValidBundle, koreaDate } from './tides.mjs';

const API_BASE = (import.meta.env.VITE_TIDE_API_BASE_URL || '').replace(/\/$/, '');

export async function loadForecast(station, now = new Date(), signal) {
  const url = API_BASE
    ? `${API_BASE}/api/tides?station=${encodeURIComponent(station)}`
    : import.meta.env.DEV
      ? `/__dev/tides?station=${encodeURIComponent(station)}`
      : null;
  if (!url || (API_BASE && !/^https:\/\//.test(API_BASE))) {
    throw new Error('API 주소가 설정되지 않았어요.');
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  if (signal) signal.addEventListener('abort', () => controller.abort(), { once: true });
  try {
    const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) throw new Error('최신 조석예보를 불러오지 못했어요.');
    const bundle = await response.json();
    if (!isValidBundle(bundle, station, koreaDate(now))) {
      throw new Error('예보가 만료됐거나 데이터가 불완전해요.');
    }
    return bundle;
  } finally {
    clearTimeout(timeout);
  }
}
