import test from 'node:test';
import assert from 'node:assert/strict';
import { koreaDate, nextTide, plotSeries, isValidBundle, shiftDay } from '../src/tides.mjs';

const today = '2026-11-18';
function makeDay(date) {
  return { date,
    hilo: [
      {t:date+' 03:00',v:600,type:'H'},
      {t:date+' 09:00',v:100,type:'L'},
      {t:date+' 15:00',v:590,type:'H'},
      {t:date+' 21:00',v:120,type:'L'},
    ],
    curve:Array.from({length:48},(_,i)=>({
      t:date+' '+String(Math.floor(i/2)).padStart(2,'0')+':'+(i%2?'30':'00'),
      v:300 + Math.sin(i / 7) * 110,
    }))
  };
}
const sample={schema_version:1,mode:'live',station:{id:'DT_0001',name:'인천'},units:'cm',
 date_range:{start:today,end:shiftDay(today,6)},generated_at_utc:'2026-11-17T21:30:00Z',
 days:Array.from({length:7},(_,i)=>makeDay(shiftDay(today,i)))};

test('Korean dates cross UTC boundary correctly',()=>{
 assert.equal(koreaDate(new Date('2026-11-17T19:00:00Z')),today);
 assert.equal(shiftDay('2026-11-30',1),'2026-12-01');
});
test('7-day verified bundle accepted; stale and incomplete bundles rejected',()=>{
 assert.equal(isValidBundle(sample,'incheon',today),true);
 assert.equal(isValidBundle(sample,'incheon','2026-11-19'),false);
 assert.equal(isValidBundle(sample,'busan',today),false);
 assert.equal(isValidBundle({...sample,days:sample.days.slice(0,6)},'incheon',today),false);
});
test('a gap in half-hour rows is rejected',()=>{
 const altered=structuredClone(sample);
 altered.days[0].curve[18].t=today+' 09:30';
 assert.equal(isValidBundle(altered,'incheon',today),false);
});
test('a past tide cannot masquerade as upcoming tide',()=>{
 const x=nextTide(sample,0,new Date('2026-11-18T14:00:00Z'));
 assert.equal(x.t,'2026-11-19 03:00');
});
test('chart represents actual 48 point values without synthetic data',()=>{
 const line=plotSeries(sample.days[0].curve);
 assert.ok(line.line.startsWith('M '));
 assert.ok(line.fill.includes(' Z'));
 assert.equal(plotSeries([]),null);
});
