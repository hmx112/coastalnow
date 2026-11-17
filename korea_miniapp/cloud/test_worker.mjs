import test from "node:test";
import assert from "node:assert/strict";
import { addDays, koreaDay, normalize, collectStation, isFresh, refreshAll, handleRequest } from "./worker.mjs";

const DAY = "2026-11-18";
const isoClock = "2026-11-17T16:12:00Z"; // 2026-11-18 01:12 KST

function provider(kind, day) {
  const rows = [];
  if (kind === "high_low") {
    for (const [time, height, event] of [
      ["02:00", "710.4", 1], ["08:00", "122", 2],
      ["14:00", "720", 3], ["20:00", "110", 4]
    ]) rows.push({predcDt: day+" "+time, predcTdlvVl:height, extrSe:event});
  } else {
    for(let i=0;i<48;i++) rows.push({
      predcDt:day+" "+String(Math.floor(i/2)).padStart(2,"0")+":"+(i%2?"30":"00"),
      tdlvHgt: String(100+i),
    });
  }
  return { response: {header:{resultCode:"00"},body:{items:{item:rows}}} };
}

function makeFetcher({fail}={}) {
  const calls=[];
  async function mockFetch(url) {
    const parsed=new URL(url);
    const kind=parsed.pathname.includes("HghLw")?"high_low":"series";
    const ymd=parsed.searchParams.get("reqDate");
    const day=ymd.slice(0,4)+"-"+ymd.slice(4,6)+"-"+ymd.slice(6);
    calls.push({kind,day,key:parsed.searchParams.get("serviceKey"),
                interval:parsed.searchParams.get("min")});
    if(fail?.({kind,day,station:parsed.searchParams.get("obsCode")})){
      return {ok:false,status:503};
    }
    return {ok:true,status:200,json:async()=>provider(kind,day)};
  }
  return {mockFetch,calls};
}

function makeKV() {
  const data=new Map();
  return {
    data,
    async get(key,kind) {const val=data.get(key);return kind==="json"&&val?JSON.parse(val):val??null;},
    async put(key,val) {data.set(key,val);},
  };
}

test("KST boundary is used; date offset is not UTC",()=>{
  assert.equal(koreaDay(new Date(isoClock)),DAY);
  assert.equal(addDays("2026-11-30",1),"2026-12-01");
});

test("official KHOA schemas have different height fields",()=>{
  assert.equal(normalize("high_low",provider("high_low",DAY),DAY)[0].v,710.4);
  assert.equal(normalize("series",provider("series",DAY),DAY).length,48);
  const wrong=provider("series",DAY);
  delete wrong.response.body.items.item[0].tdlvHgt;
  assert.throws(()=>normalize("series",wrong,DAY),/height/);
});

test("incomplete 30-minute series cannot enter cache",()=>{
  const bad=provider("series",DAY);
  bad.response.body.items.item.splice(17,1);
  assert.throws(()=>normalize("series",bad,DAY),/Incomplete/);
});

test("one station collects 7 complete days; separate service keys",async()=>{
  const {mockFetch,calls}=makeFetcher();
  const result=await collectStation("incheon",DAY,{
    KHOA_HIGH_LOW_KEY:"KEY_HIGH",
    KHOA_SERIES_KEY:"KEY_SERIES",
  },mockFetch);
  assert.equal(result.days.length,7);
  assert.equal(calls.length,14);
  assert.equal(result.days[6].date,"2026-11-24");
  assert.equal(calls.filter(c=>c.kind==="high_low"&&c.key==="KEY_HIGH").length,7);
  assert.equal(calls.filter(c=>c.kind==="series"&&c.key==="KEY_SERIES"&&c.interval==="30").length,7);
  assert.equal(isFresh(result,DAY),true);
  assert.equal(isFresh(result,"2026-11-19"),false);
});

test("42 provider calls and exactly 3 KV writes for 3 stations",async()=>{
  const kv=makeKV();
  const {mockFetch,calls}=makeFetcher();
  const names=await refreshAll({
    TIDES_KV:kv,KHOA_HIGH_LOW_KEY:"KEY_HIGH",KHOA_SERIES_KEY:"KEY_SERIES"
  },new Date(isoClock),mockFetch);
  assert.deepEqual(names,["incheon","busan","jeju"]);
  assert.equal(calls.length,42);
  assert.equal(kv.data.size,3);
  const result=await handleRequest(new Request("https://example.com/api/tides?station=jeju"),
    {TIDES_KV:kv},new Date(isoClock));
  assert.equal(result.status,200);
  const payload=await result.json();
  assert.equal(payload.days.length,7);
  assert.equal(result.headers.get("cache-control"),"public, max-age=300");
  assert.equal(JSON.stringify(payload).includes("KEY_HIGH"),false);
});

test("a provider outage preserves previous station cache and reports failure",async()=>{
  const kv=makeKV();kv.data.set("tides:v1:incheon",JSON.stringify({marker:"previous"}));
  const {mockFetch}=makeFetcher({fail:({kind,station})=>kind==="series"&&station==="DT_0001"});
  await assert.rejects(()=>refreshAll({
    TIDES_KV:kv,KHOA_HIGH_LOW_KEY:"A",KHOA_SERIES_KEY:"B",
  },new Date(isoClock),mockFetch),/stations failed/);
  assert.equal(JSON.parse(kv.data.get("tides:v1:incheon")).marker,"previous");
  assert.equal(kv.data.size,3); // Other stations should complete independently
});

test("stale/missing cached data is not shown as current",async()=>{
  const kv=makeKV();
  let result=await handleRequest(new Request("https://example.com/api/tides?station=incheon"),
    {TIDES_KV:kv},new Date(isoClock));
  assert.equal(result.status,503);
  const response=await result.json();
  assert.equal(response.reason,"not_fresh");
  result=await handleRequest(new Request("https://example.com/api/tides?station=undefined"),
    {TIDES_KV:kv},new Date(isoClock));
  assert.equal(result.status,400);
});
