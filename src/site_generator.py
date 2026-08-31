"""Render directory pages with the San Diego v3 visual language."""
import json
from collections import defaultdict
from html import escape

from activities.registry import enabled_activities
from locations import LOCATIONS
from seo import breadcrumb_json_ld, canonical_url

LOGO='''<span class="logo-mark"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 8c3.5-4 6.5 4 10 0s6.5 4 8 0M3 13c3.5-4 6.5 4 10 0s6.5 4 8 0M3 18c3.5-4 6.5 4 10 0s6.5 4 8 0" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round"/></svg></span>'''
PINTEREST_DOMAIN_VERIFY='<meta name="p:domain_verify" content="2d1606bc6882843fbb5143b963ef1cc2">'

def location_status(x): return x.get('status','Preview')

def _groups():
 g=defaultdict(list)
 for x in LOCATIONS.values(): g[x['state_slug']].append(x)
 return {k:sorted(v,key=lambda x:x['name']) for k,v in sorted(g.items())}

def _badge(x):
 s=location_status(x); c='badge-live' if s=='Live NOAA' else 'badge-preview'
 return f'<span class="status-badge {c}">{s}</span>'

def _card(x,href): return f'<a class="info-card location-card" href="{escape(href)}">{_badge(x)}<h3>{escape(x["name"])}</h3><p>{escape(x["state"])} · Today + 7-day view</p><span class="card-arrow">View location →</span></a>'

def _activity_card(activity):
 label=escape(activity['label']); slug=escape(activity['slug'])
 return f'<a class="info-card activity-directory-card" href="{slug}/index.html"><span class="state-code">ACTIVITY</span><h3>{label}</h3><p>Compare today and tomorrow across CoastalNow locations.</p><span class="card-arrow">Explore {label.lower()} →</span></a>'

def _hero(eyebrow,title,copy): return f'''<section class="hero"><div class="hero-inner"><div><p class="eyebrow">{escape(eyebrow)}</p><h1>{escape(title)}</h1><p class="hero-copy">{escape(copy)}</p></div><div class="hero-date"><span>DIRECTORY STATUS</span><strong>NOAA-ready locations</strong><small>Live data and preview pages clearly marked</small></div></div><svg class="hero-wave" viewBox="0 0 520 170" aria-hidden="true"><path d="M0 110 C90 25 155 155 255 75 S400 35 540 100"/><path d="M0 145 C90 60 155 180 255 110 S400 70 540 135"/></svg><i class="hero-bubble b1"></i><i class="hero-bubble b2"></i></section>'''

def _shell(title,desc,prefix,body,canonical_path,breadcrumbs):
 canonical=canonical_url(canonical_path)
 structured=breadcrumb_json_ld(breadcrumbs)
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{PINTEREST_DOMAIN_VERIFY}<title>{escape(title)}</title><meta name="description" content="{escape(desc)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}">{structured}<link rel="stylesheet" href="{prefix}assets/site.css"></head><body><header class="site-header"><div class="wrap header-inner"><a class="brand" href="{prefix}index.html">{LOGO}<span>CoastalNow</span></a><nav class="nav"><a href="{prefix}index.html">Home</a><a href="{prefix}index.html#states">States</a><a class="search-pill" href="{prefix}index.html#search">Search</a></nav></div></header><main class="wrap">{body}</main><footer><div class="wrap footer-inner"><strong>CoastalNow</strong><div class="footer-links"><a href="{prefix}about/index.html">About</a><a href="{prefix}privacy/index.html">Privacy</a><a href="{prefix}contact/index.html">Contact</a></div></div></footer></body></html>'''

def _state_card(slug,items): return f'<a class="info-card state-card" href="tides/{slug}/index.html"><span class="state-code">{items[0]["state_code"]}</span><h3>{items[0]["state"]}</h3><p>{len(items)} coastal locations</p><span class="card-arrow">Browse state →</span></a>'

def _home(groups):
 all_items=sorted((x for v in groups.values() for x in v),key=lambda x:x['name'].casefold()); data=json.dumps([{'name':x['name'],'state':x['state'],'url':x['page_path'],'status':location_status(x)} for x in all_items],ensure_ascii=False)
 activities=enabled_activities()
 body=_hero('COASTAL TIDE DIRECTORY','Find tide times by coastal location.','A clear starting point for today’s tide times, NOAA pages and coastal location guides.')
 body+=f'''<section class="section" id="search"><div class="section-head"><h2>Find a beach or city</h2><p>Search {len(all_items)} coastal locations</p></div><div class="search-box"><input id="q" placeholder="San Diego, Florida, Holden Beach…"><button onclick="go()">Search</button></div><div id="results" class="directory-grid"></div></section>'''
 if activities:
  body+=f'''<section class="section" id="activities"><div class="section-head"><h2>Explore by activity</h2><p>Compare coastal conditions by what you want to do</p></div><div class="directory-grid">{"".join(_activity_card(item) for item in activities)}</div></section>'''
 body+=f'''<section class="section" id="states"><div class="section-head"><h2>Browse by state</h2><p>State directories</p></div><div class="directory-grid">{"".join(_state_card(k,v) for k,v in groups.items())}</div></section><section class="section"><div class="section-head"><h2>All coastal locations</h2><p>Live NOAA and Preview status</p></div><div class="directory-grid">{"".join(_card(x,x["page_path"]) for x in all_items)}</div></section><div class="ad-slot"><span>ADVERTISEMENT</span></div><script>const L={data};function go(){{const q=document.getElementById('q').value.toLowerCase().trim();document.getElementById('results').innerHTML=q?L.filter(x=>(x.name+' '+x.state).toLowerCase().includes(q)).slice(0,12).map(x=>`<a class="info-card" href="${{x.url}}"><span class="status-badge ${{x.status==='Live NOAA'?'badge-live':'badge-preview'}}">${{x.status}}</span><h3>${{x.name}}</h3><p>${{x.state}}</p></a>`).join('')||'<p>No result</p>':''}}</script>'''
 return _shell('CoastalNow — Tide Times by U.S. Coastal Location','Browse tide times by U.S. coastal location.','',body,'',[('Home','')])

def _state_page(items):
 name=items[0]['state']; slug=items[0]['state_slug']; cards=''.join(_card(x,x['slug']+'/index.html') for x in items)
 body=f'<div class="breadcrumbs"><a href="../../index.html">Home</a><span>/</span>{escape(name)}</div>'+_hero(f'{items[0]["state_code"]} DIRECTORY',f'{name} Tide Times',f'Browse {len(items)} coastal locations with the same clear status and page layout.')+f'<section class="section"><div class="section-head"><h2>Choose a coastal location</h2><p>{len(items)} locations</p></div><div class="directory-grid">{cards}</div></section><div class="ad-slot"><span>ADVERTISEMENT</span></div>'
 path=f'tides/{slug}/index.html'
 return _shell(f'{name} Tide Times | CoastalNow',f'Browse tide pages for coastal locations in {name}.','../../',body,path,[('Home',''),(name,path)])

def build_directory_pages():
 g=_groups(); return {'index.html':_home(g),**{f'tides/{k}/index.html':_state_page(v) for k,v in g.items()}}
