import { isValidBundle, koreaDate, remainingForecastDays } from './tides.mjs';

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
    if (!response.ok) {
      throw new Error(import.meta.env.DEV && !API_BASE
        ? '로컬 예보 파일을 찾을 수 없어요. korea_miniapp 폴더에서 run_week_check.ps1을 실행해 주세요.'
        : '조석예보 서버에 연결할 수 없어요. 잠시 후 다시 이용해 주세요.');
    }
    const bundle = await response.json();
    const today = koreaDate(now);
    if (!isValidBundle(bundle, station, today)) {
      if (bundle?.date_range?.end && today > bundle.date_range.end) {
        throw new Error('저장된 예보가 만료됐어요. 7일 예보 데이터를 다시 수집해 주세요.');
      }
      throw new Error('예보 날짜나 데이터 형식이 올바르지 않아요. 데이터를 다시 수집해 주세요.');
    }
    // Today's forecast may be part of a bundle collected 1–6 days earlier.
    // Drop expired dates but retain the original source/generated_at metadata.
    return { ...bundle, days: remainingForecastDays(bundle, today) };
  } finally {
    clearTimeout(timeout);
  }
}
