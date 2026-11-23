/** Official test IDs are never selected for the release bundle. */
export const OFFICIAL_TEST_IDS = Object.freeze({
  banner: 'ait-ad-test-banner-id',
  rewarded: 'ait-ad-test-rewarded-id',
});
function validLiveId(id) {
  const s = typeof id === 'string' ? id.trim() : '';
  return s.length > 0 && !s.startsWith('ait-ad-test-');
}
export function configureAds({ dev = false, mode = 'production', bannerId = '', rewardedId = '' } = {}) {
  const testing = dev || mode === 'adtest';
  const banner = testing ? OFFICIAL_TEST_IDS.banner : (validLiveId(bannerId) ? bannerId.trim() : null);
  const rewarded = testing ? OFFICIAL_TEST_IDS.rewarded : (validLiveId(rewardedId) ? rewardedId.trim() : null);
  return Object.freeze({ testing, banner, rewarded });
}
