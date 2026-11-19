import React, { useEffect, useMemo, useState } from 'react';
import { Button, Badge } from '@toss/tds-mobile';
import { Storage, User } from '@apps-in-toss/web-framework';
import { loadForecast } from './api.mjs';
import { STATIONS, STATION_SLUGS, koreaDate, displayDate, asTime, asHeight, nextTide, plotSeries } from './tides.mjs';

const PREFERENCE_KEY = 'oneul-bada:starting-station-v1';
let anonymousKeyTask;
function ensureAnonymousKeyOnce() {
  if (!anonymousKeyTask) anonymousKeyTask = User.getAnonymousKey().catch(() => null);
  return anonymousKeyTask;
}

function readLocalPreference() {
  try {
    const candidate = window.localStorage.getItem(PREFERENCE_KEY);
    return STATION_SLUGS.includes(candidate) ? candidate : 'incheon';
  } catch { return 'incheon'; }
}

function ShortTideChart({ rows }) {
  const chart = useMemo(() => plotSeries(rows), [rows]);
  if (!chart) return <p className="empty-graph">조위 그래프를 표시할 수 없어요.</p>;
  return (
    <div className="chart-section">
      <div className="chart-scale">
        <span>최고 {asHeight(chart.maximum)}</span>
        <span>최저 {asHeight(chart.minimum)}</span>
      </div>
      <svg viewBox="0 0 332 170" role="img" aria-label="오늘 시간대별 예측 조위 그래프" preserveAspectRatio="none" className="tide-chart">
        <defs>
          <linearGradient id="tide-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#63BAC7" stopOpacity=".3" />
            <stop offset="1" stopColor="#63BAC7" stopOpacity=".015" />
          </linearGradient>
        </defs>
        {[35, 87, 140].map(y => <line key={y} x1="14" x2="318" y1={y} y2={y} stroke="#E7EFF2" strokeDasharray="3 4" />)}
        <path d={chart.fill} fill="url(#tide-gradient)" />
        <path d={chart.line} fill="none" stroke="#168FA9" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="chart-hours" aria-hidden="true"><span>00시</span><span>06시</span><span>12시</span><span>18시</span><span>24시</span></div>
    </div>
  );
}

function EventCards({ events }) {
  return (
    <div className="events-grid">
      {events.map((item, i) => <div key={item.t + i} className="event-card">
        <div className={'event-kind ' + (item.type === 'H' ? 'high' : 'low')}>
          <span aria-hidden="true">{item.type === 'H' ? '↑' : '↓'}</span> {item.type === 'H' ? '만조' : '간조'}
        </div>
        <strong>{asTime(item.t)}</strong>
        <span className="event-height">예측 조위 {asHeight(item.v)}</span>
      </div>)}
    </div>
  );
}

function dateCaption(today) {
  const [year, month, day] = today.split('-');
  return `${year}년 ${Number(month)}월 ${Number(day)}일`;
}

export default function App() {
  const [station, setStation] = useState(readLocalPreference);
  const [savedStation, setSavedStation] = useState(readLocalPreference);
  const [bundle, setBundle] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const today = koreaDate();

  useEffect(() => {
    let active = true;
    // Issue an anonymous key without introducing a login gate. Do not log or transmit it.
    void ensureAnonymousKeyOnce();
    Storage.getItem(PREFERENCE_KEY).then(value => {
      if (active && STATION_SLUGS.includes(value)) {
        setSavedStation(value);
        setStation(value);
      }
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setBundle(null);
    setSelectedIndex(0);
    loadForecast(station, new Date(), controller.signal)
      .then(data => { if (!controller.signal.aborted) setBundle(data); })
      .catch((err) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : '예보를 불러오지 못했어요.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [station, reloadToken]);

  async function saveFavorite() {
    setSavedStation(station);
    try { window.localStorage.setItem(PREFERENCE_KEY, station); } catch { /* Local cache unavailable */ }
    try { await Storage.setItem(PREFERENCE_KEY, station); } catch { /* Browser fallback already saved */ }
  }

  const days = bundle?.days || [];
  const selected = days[selectedIndex];
  const upcoming = selected ? nextTide(bundle, selectedIndex) : null;
  const isNextDay = selectedIndex === 0 && upcoming && !upcoming.t.startsWith(today);
  const saved = station === savedStation;
  const dateInfo = selected ? displayDate(selected.date) : '';
  const updated = bundle ? new Date(bundle.generated_at_utc) : null;

  return (
    <main className="shell" aria-label="오늘의 바다 조석예보">
      <div className="page-title">
        <div className="heading-col">
          <p className="kicker">MY OCEAN</p>
          <h1>오늘의 바다</h1>
          <p>자주 찾는 바다의 물때를 편하게 확인해요.</p>
        </div>
        <div className="wave-mark" aria-hidden="true">≈</div>
      </div>

      <section className="station-panel" aria-label="지역 선택 및 저장">
        <div className="station-top">
          <div>
            <label htmlFor="station" className="kicker">보고 싶은 해역</label>
            <div className="select-wrap">
              <span className="pin" aria-hidden="true">⌖</span>
              <select value={station} onChange={(e) => setStation(e.target.value)} id="station">
                {STATION_SLUGS.map(slug => <option value={slug} key={slug}>{STATIONS[slug].name}</option>)}
              </select>
            </div>
          </div>
          <Button color="primary" variant="weak" size="small" onClick={saveFavorite} disabled={saved}>
            {saved ? '시작 지역으로 저장했어요' : '시작 지역으로 저장'}
          </Button>
        </div>
        <div className="source-status">
          <Badge variant="weak" size="small" color="teal">국립해양조사원 예보</Badge>
          <span>{dateCaption(today)} 조회</span>
        </div>
      </section>

      {loading && <section className="feedback" role="status"><div className="spinner" aria-hidden="true" /> 최신 예보를 불러오고 있어요.</section>}
      {!loading && error && <section className="feedback problem" role="alert">
        <div className="feedback-icon" aria-hidden="true">!</div>
        <h2>지금은 예보를 표시할 수 없어요.</h2>
        <p>{error}</p>
        <Button color="primary" size="large" display="full" onClick={() => setReloadToken(x => x + 1)}>
          다시 불러오기
        </Button>
      </section>}

      {!loading && !error && selected && <>
        <section className="days-section" aria-label="예보 날짜 선택">
          <div className="section-heading"><h2>{days.length}일 조석예보</h2><span>남은 날짜를 선택해 보세요</span></div>
          <div className="days-scroller">
            {days.map((day, i) => {
              const weekday = new Date(day.date + 'T00:00:00Z').toLocaleDateString('ko-KR', { weekday:'short', timeZone:'UTC' });
              return <button
                key={day.date}
                type="button"
                className={'day-pill' + (i === selectedIndex ? ' selected' : '')}
                aria-pressed={i === selectedIndex}
                aria-label={displayDate(day.date) + ' 예보'}
                onClick={() => setSelectedIndex(i)}>
                <span>{i === 0 ? '오늘' : weekday}</span>
                <strong>{Number(day.date.slice(-2))}</strong>
              </button>;
            })}
          </div>
        </section>

        <section className="next-tide-card" aria-label="다음 만조 간조 시각">
          <div className="small-heading">{selectedIndex === 0 ? '다음 물때' : '선택한 날의 첫 물때'}</div>
          <div className="next-main">
            <div>
              <p className="next-kind">{upcoming?.type === 'H' ? '만조' : upcoming?.type === 'L' ? '간조' : '예보 없음'}</p>
              <strong>{upcoming ? asTime(upcoming.t) : '—'}</strong>
              <p className="next-value">예측 조위 {upcoming ? asHeight(upcoming.v) : '—'}</p>
            </div>
            <div className="tide-sigil" aria-hidden="true"><span>≈</span></div>
          </div>
          <p className="next-date">{isNextDay ? '다음 날의 첫 물때예요' : dateInfo} · 한국표준시(KST)</p>
        </section>

        <section className="data-card" aria-labelledby="chart-heading">
          <div className="section-heading"><h2 id="chart-heading">시간별 조위 변화</h2><span>30분 단위 · cm</span></div>
          <ShortTideChart rows={selected.curve} />
          <p className="card-hint">예측된 해수면 높이이며, 실제 수심이나 안전 여부를 뜻하지 않아요.</p>
        </section>

        <section className="data-card" aria-labelledby="events-heading">
          <div className="section-heading"><h2 id="events-heading">만조 · 간조</h2><span>{dateInfo}</span></div>
          <EventCards events={selected.hilo} />
        </section>

        <section className="disclosure" aria-label="자료와 주의사항">
          <strong>조석예보 안내</strong>
          <p>이 자료는 국립해양조사원에서 제공한 조석예보예요. 실제 관측 수위나 기상특보를 대신하지 않아요.</p>
          <p>자료 수집 시각: {Number.isFinite(updated?.getTime()) ? updated.toLocaleString('ko-KR', {timeZone:'Asia/Seoul', dateStyle:'medium', timeStyle:'short'}) : '확인할 수 없어요'}</p>
          {Number.isFinite(updated?.getTime()) && Date.now() - updated.getTime() > 24 * 60 * 60 * 1000 &&
            <p className="stale-notice">수집 후 하루가 지난 예보예요. 최근 갱신 자료가 필요하면 다시 수집해 주세요.</p>}
        </section>
      </>}
      <div className="bottom-pad" />
    </main>
  );
}
