import { rewardEventEarned } from './rewards.mjs';
/** SDK event adapter: dismissed/clicked/impression cannot grant the reward. */
export function createRewardController({ sdk, adGroupId, onStatus = () => {}, onReward = () => {} }) {
  let phase = 'idle', disposed = false, earned = false;
  let unsubscribeLoad = () => {}, unsubscribeShow = () => {};
  function status(next) {
    if (disposed) return;
    phase = next; onStatus(next);
  }
  function supported() {
    return Boolean(adGroupId && sdk?.loadFullScreenAd?.isSupported?.() &&
      sdk?.showFullScreenAd?.isSupported?.());
  }
  function load() {
    if (disposed) return;
    if (!supported()) { status('unavailable'); return; }
    unsubscribeLoad();
    status('loading');
    try {
      const unsub = sdk.loadFullScreenAd({
        options: { adGroupId },
        onEvent: event => {
          if (!disposed && event?.type === 'loaded' && phase === 'loading') status('ready');
        },
        onError: () => status('failed'),
      });
      unsubscribeLoad = typeof unsub === 'function' ? unsub : () => {};
    } catch { status('failed'); }
  }
  function show() {
    if (disposed || phase !== 'ready' || !supported()) return false;
    earned = false;
    unsubscribeShow();
    status('showing');
    try {
      const unsub = sdk.showFullScreenAd({
        options: { adGroupId },
        onEvent: event => {
          if (disposed) return;
          if (rewardEventEarned(event) && phase === 'showing' && !earned) {
            earned = true;
            onReward(event.data);
            status('earned');
          } else if (event?.type === 'dismissed') {
            unsubscribeShow();
            unsubscribeShow = () => {};
            if (!earned) load();
          } else if (event?.type === 'failedToShow') {
            status('failed');
          }
        },
        onError: () => status('failed'),
      });
      unsubscribeShow = typeof unsub === 'function' ? unsub : () => {};
      return true;
    } catch { status('failed'); return false; }
  }
  function dispose() {
    disposed = true;
    unsubscribeLoad(); unsubscribeShow();
    unsubscribeLoad = () => {}; unsubscribeShow = () => {};
  }
  return {load, show, retry:load, dispose, get phase(){return phase;}};
}
