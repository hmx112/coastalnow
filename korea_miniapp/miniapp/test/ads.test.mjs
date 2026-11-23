import test from 'node:test';
import assert from 'node:assert/strict';
import { configureAds, OFFICIAL_TEST_IDS } from '../src/ads/config.mjs';
import { hasWeeklyAccess, nextAccessExpiry, REWARD_DURATION_MS, rewardEventEarned } from '../src/ads/rewards.mjs';
import { createRewardController } from '../src/ads/reward-controller.mjs';
import { weeklyOverview } from '../src/ads/weekly.mjs';

test('only development or explicit adtest builds use official test IDs',()=>{
 assert.equal(configureAds({dev:true,mode:'development'}).banner,OFFICIAL_TEST_IDS.banner);
 assert.equal(configureAds({mode:'adtest'}).rewarded,OFFICIAL_TEST_IDS.rewarded);
 assert.deepEqual(configureAds({mode:'production'}),{testing:false,banner:null,rewarded:null});
 assert.equal(configureAds({mode:'production',bannerId:OFFICIAL_TEST_IDS.banner}).banner,null);
 assert.equal(configureAds({mode:'production',bannerId:'ait.v2.live.banner'}).banner,'ait.v2.live.banner');
});
test('only a positive native reward event can grant local, 24-hour access',()=>{
 for(const type of ['requested','show','impression','clicked','dismissed','failedToShow'])
   assert.equal(rewardEventEarned({type,data:{unitType:'weekly',unitAmount:1}}),false);
 assert.equal(rewardEventEarned({type:'userEarnedReward',data:{unitType:'weekly',unitAmount:1}}),true);
 assert.equal(rewardEventEarned({type:'userEarnedReward',data:{unitType:'weekly',unitAmount:0}}),false);
 const now=Date.UTC(2026,10,20);
 assert.equal(nextAccessExpiry(now)-now,REWARD_DURATION_MS);
 assert.equal(hasWeeklyAccess(now+REWARD_DURATION_MS,now+REWARD_DURATION_MS-1),true);
 assert.equal(hasWeeklyAccess(now+REWARD_DURATION_MS,now+REWARD_DURATION_MS),false);
});
function fakeSDK() {
 let loadEvent,showEvent,showError;
 const calls=[];
 function loadFullScreenAd({options,onEvent}) {
   calls.push(['load',options.adGroupId]);loadEvent=onEvent;return ()=>{};
 }
 function showFullScreenAd({options,onEvent,onError}) {
   calls.push(['show',options.adGroupId]);showEvent=onEvent;showError=onError;return ()=>{};
 }
 loadFullScreenAd.isSupported=()=>true;
 showFullScreenAd.isSupported=()=>true;
 return {sdk:{loadFullScreenAd,showFullScreenAd},calls,
   loaded:()=>loadEvent({type:'loaded'}),send:e=>showEvent(e),
   fail:()=>showError(new Error('native ad unavailable'))};
}
test('show requires load; early close never unlocks; reward fires once',()=>{
 const f=fakeSDK();let grants=0;
 const c=createRewardController({sdk:f.sdk,adGroupId:'TEST',onReward:()=>grants++});
 assert.equal(c.show(),false);c.load();assert.equal(c.show(),false);f.loaded();
 assert.equal(c.show(),true);f.send({type:'clicked'});f.send({type:'dismissed'});
 assert.equal(grants,0);
 assert.equal(f.calls.filter(([name])=>name==='load').length,2);
 f.loaded();assert.equal(c.show(),true);
 f.send({type:'userEarnedReward',data:{unitType:'weekly',unitAmount:1}});
 f.send({type:'userEarnedReward',data:{unitType:'weekly',unitAmount:1}});
 f.send({type:'dismissed'});
 assert.equal(grants,1);assert.equal(c.show(),false);c.dispose();
});
test('native SDK errors never trigger a reward',()=>{
 const f=fakeSDK();let grants=0;
 const c=createRewardController({sdk:f.sdk,adGroupId:'TEST',onReward:()=>grants++});
 c.load();f.loaded();c.show();f.fail();
 assert.equal(c.phase,'failed');assert.equal(c.show(),false);
 assert.equal(grants,0);c.dispose();
});
test('comparison calculates only actual already-fetched extremes',()=>{
 const rows=weeklyOverview([{date:'2026-11-20',hilo:[
  {t:'2026-11-20 03:00',v:520,type:'H'},
  {t:'2026-11-20 09:00',v:180,type:'L'},
  {t:'2026-11-20 15:00',v:600,type:'H'},
  {t:'2026-11-20 21:00',v:170,type:'L'},
 ]}]);
 assert.deepEqual(rows,[{date:'2026-11-20',highTime:'15:00',lowTime:'21:00',highCm:600,lowCm:170,rangeCm:430}]);
});
