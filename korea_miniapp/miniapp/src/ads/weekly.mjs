/** Only uses already verified official high/low data. No extra KHOA API calls. */
export function weeklyOverview(days) {
  if (!Array.isArray(days)) return [];
  return days.map(day => {
    const highs = (day.hilo ?? []).filter(event => event.type === 'H' && Number.isFinite(event.v));
    const lows = (day.hilo ?? []).filter(event => event.type === 'L' && Number.isFinite(event.v));
    if (!highs.length || !lows.length) return null;
    const maxHigh = highs.reduce((a,b) => b.v > a.v ? b : a);
    const minLow = lows.reduce((a,b) => b.v < a.v ? b : a);
    return {
      date: day.date,
      highTime: maxHigh.t.slice(-5), lowTime: minLow.t.slice(-5),
      highCm: maxHigh.v, lowCm: minLow.v,
      rangeCm: Math.round((maxHigh.v - minLow.v) * 10) / 10,
    };
  }).filter(Boolean);
}
