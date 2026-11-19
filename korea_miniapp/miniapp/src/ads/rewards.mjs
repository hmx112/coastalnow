/** Local convenience feature access, never cash or transferable points. */
export const REWARD_STORAGE_KEY = 'oneul-bada:weekly-overview-until:v1';
export const REWARD_DURATION_MS = 24 * 60 * 60 * 1000;
export function hasWeeklyAccess(until, now = Date.now()) {
  const parsed = Number(until);
  return Number.isSafeInteger(parsed) && parsed > now && parsed <= now + REWARD_DURATION_MS;
}
export function rewardEventEarned(event) {
  return event?.type === 'userEarnedReward' &&
    typeof event.data?.unitType === 'string' &&
    event.data.unitType.length > 0 &&
    Number.isFinite(event.data?.unitAmount) && event.data.unitAmount > 0;
}
export function nextAccessExpiry(now = Date.now()) { return now + REWARD_DURATION_MS; }
export function readWeeklyAccess(storage, now = Date.now()) {
  try {
    const until = storage.getItem(REWARD_STORAGE_KEY);
    return hasWeeklyAccess(until, now) ? Number(until) : 0;
  } catch { return 0; }
}
export function storeWeeklyAccess(storage, expiry) {
  try { storage.setItem(REWARD_STORAGE_KEY, String(expiry)); } catch { /* Session state remains. */ }
}
