import React, { useEffect, useRef, useState } from 'react';
import { TossAds } from '@apps-in-toss/web-framework';

let initializePromise;
function initializeOnce() {
  if (!TossAds.initialize.isSupported() || !TossAds.attachBanner.isSupported())
    return Promise.resolve(false);
  if (!initializePromise) {
    initializePromise = new Promise(resolve => {
      try {
        TossAds.initialize({ callbacks: {
          onInitialized: () => resolve(true),
          onInitializationFailed: () => resolve(false),
        }});
      } catch { resolve(false); }
    });
  }
  return initializePromise;
}

/** One banner, SDK-owned visuals and refresh only; never style or click overlay ads. */
export function BannerAd({ adGroupId, enabled }) {
  const target = useRef(null);
  const [state, setState] = useState('pending');
  const preview = import.meta.env.DEV;
  useEffect(() => {
    if (!enabled || !adGroupId) return;
    let disposed = false, instance;
    if (!TossAds.initialize.isSupported() || !TossAds.attachBanner.isSupported()) {
      setState(preview ? 'preview' : 'unsupported');
      return;
    }
    initializeOnce().then(ready => {
      if (disposed) return;
      if (!ready || !target.current) { setState('unsupported'); return; }
      setState('loading');
      try {
        instance = TossAds.attachBanner(adGroupId, target.current, {
          theme:'light', tone:'blackAndWhite', variant:'expanded',
          callbacks:{
            onAdRendered: () => { if (!disposed) setState('rendered'); },
            onNoFill: () => { if (!disposed) setState('no-fill'); },
            onAdFailedToRender: () => { if (!disposed) setState('failed'); },
          },
        });
      } catch { setState('failed'); }
    });
    return () => {
      disposed = true;
      try { instance?.destroy(); } catch { /* native teardown */ }
    };
  }, [adGroupId, enabled, preview]);
  if (!enabled || !adGroupId) return null;
  const hidden = ['unsupported','no-fill','failed'].includes(state);
  return (
    <section className={'banner-ad-area' + (hidden ? ' banner-ad-hidden' : '')} aria-label="광고 영역">
      {state !== 'preview' && <span className="ad-kind-label">광고</span>}
      {state === 'preview' && <div className="banner-ad-preview" aria-label="테스트용 배너 위치 미리보기">
        <span>광고 영역 미리보기</span><small>실제 광고가 아닙니다 · 토스 앱에서 테스트</small>
      </div>}
      <div ref={target} className="toss-banner-slot"
        style={state === 'preview' ? {height:0} : undefined}
        aria-hidden={state === 'preview'} />
    </section>
  );
}
