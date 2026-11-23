import React, { useEffect, useRef, useState } from 'react';
import { Button } from '@toss/tds-mobile';
import { loadFullScreenAd, showFullScreenAd } from '@apps-in-toss/web-framework';
import { createRewardController } from './reward-controller.mjs';
import { weeklyOverview } from './weekly.mjs';
import { hasWeeklyAccess, nextAccessExpiry, readWeeklyAccess, storeWeeklyAccess } from './rewards.mjs';
import { asHeight, displayDate } from '../tides.mjs';

function WeekTable({ days }) {
  const rows = weeklyOverview(days);
  return <div className="weekly-overview" aria-label="날짜별 만조 간조 조차 비교">
    <div className="weekly-overview-head"><span>날짜</span><span>가장 높은 만조</span><span>가장 낮은 간조</span><span>조차</span></div>
    {rows.map(row => <div className="weekly-overview-row" key={row.date}>
      <strong>{displayDate(row.date)}</strong>
      <div><b>{row.highTime}</b><small>{asHeight(row.highCm)}</small></div>
      <div><b>{row.lowTime}</b><small>{asHeight(row.lowCm)}</small></div>
      <strong className="tide-difference">{asHeight(row.rangeCm)}</strong>
    </div>)}
    <p className="card-hint">조차는 하루의 최고 만조와 최저 간조 사이 높이 차이입니다. 해양활동의 안전성이나 실제 수심을 나타내지 않아요.</p>
  </div>;
}

const sdk = { loadFullScreenAd, showFullScreenAd };
export function RewardedComparison({ adGroupId, days = [] }) {
  const [expiry, setExpiry] = useState(() => {
    try { return readWeeklyAccess(window.localStorage); } catch { return 0; }
  });
  const unlocked = hasWeeklyAccess(expiry);
  const [status, setStatus] = useState('idle');
  const controllerRef = useRef(null);
  useEffect(() => {
    if (unlocked || !adGroupId) {
      setStatus(adGroupId ? 'earned' : 'unavailable');
      return;
    }
    const controller = createRewardController({
      sdk, adGroupId,
      onStatus: setStatus,
      onReward: () => {
        const next = nextAccessExpiry();
        try { storeWeeklyAccess(window.localStorage, next); } catch {}
        setExpiry(next);
      },
    });
    controllerRef.current = controller;
    controller.load();
    return () => {
      controller.dispose();
      if (controllerRef.current === controller) controllerRef.current = null;
    };
  }, [adGroupId, unlocked]);

  if (days.length < 2) return null;
  const ready = status === 'ready';
  const busy = ['loading', 'showing'].includes(status);
  return (
    <section className="data-card rewarded-feature" aria-labelledby="rewarded-title">
      <div className="section-heading"><h2 id="rewarded-title">여러 날 물때 한눈에 비교</h2><span>추가 편의 기능</span></div>
      {unlocked ? <>
        <p className="reward-status">비교표 이용 가능 · 광고 시청 없이 24시간 제공</p>
        <WeekTable days={days} />
      </> : <>
        <p className="reward-description">날짜마다 확인하지 않고, 남은 예보 기간의 최고 만조·최저 간조와 조차를 한 화면에서 비교해요.</p>
        <p className="reward-terms">선택형 리워드 광고를 시청하고 보상을 획득하면 24시간 열람할 수 있어요. 기본 조석예보는 언제나 무료예요.</p>
        <Button color="primary" size="large" display="full" disabled={!ready}
          onClick={() => controllerRef.current?.show()}>
          {ready ? '광고 보고 24시간 비교표 열기' : busy ? '광고를 준비하거나 표시하고 있어요' : '현재 광고를 이용할 수 없어요'}
        </Button>
        {status === 'failed' && <button type="button" className="reward-retry"
          onClick={() => controllerRef.current?.retry()}>광고 다시 준비하기</button>}
        {status === 'unavailable' && <p className="reward-help">토스 앱에서 광고를 지원하는 환경일 때 이용할 수 있어요.</p>}
      </>}
    </section>
  );
}
