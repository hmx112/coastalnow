"""Render directory and trust pages with the San Diego v3 visual language."""
import json
from collections import defaultdict
from html import escape

from activities.registry import enabled_activities
from locations import LOCATIONS
from seo import breadcrumb_json_ld, canonical_url
from state_landing import items_for_slugs, state_landing_config, state_region_items

LOGO='''<span class="logo-mark"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 8c3.5-4 6.5 4 10 0s6.5 4 8 0M3 13c3.5-4 6.5 4 10 0s6.5 4 8 0M3 18c3.5-4 6.5 4 10 0s6.5 4 8 0" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round"/></svg></span>'''
PINTEREST_DOMAIN_VERIFY='<meta name="p:domain_verify" content="2d1606bc6882843fbb5143b963ef1cc2">'
FAVICON_LINKS='<link rel="icon" type="image/png" sizes="192x192" href="/favicon.png"><link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">'

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

def _hero(eyebrow,title,copy): return f'''<section class="hero"><div class="hero-inner"><div><p class="eyebrow">{escape(eyebrow)}</p><h1>{escape(title)}</h1><p class="hero-copy">{escape(copy)}</p></div><div class="hero-date"><span>DIRECTORY STATUS</span><strong>NOAA-ready locations</strong><small>Live data and source details clearly marked</small></div></div><svg class="hero-wave" viewBox="0 0 520 170" aria-hidden="true"><path d="M0 110 C90 25 155 155 255 75 S400 35 540 100"/><path d="M0 145 C90 60 155 180 255 110 S400 70 540 135"/></svg><i class="hero-bubble b1"></i><i class="hero-bubble b2"></i></section>'''

def _shell(title,desc,prefix,body,canonical_path,breadcrumbs):
 canonical=canonical_url(canonical_path)
 structured=breadcrumb_json_ld(breadcrumbs)
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{PINTEREST_DOMAIN_VERIFY}{FAVICON_LINKS}<title>{escape(title)}</title><meta name="description" content="{escape(desc)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}">{structured}<link rel="stylesheet" href="{prefix}assets/site.css"></head><body><header class="site-header"><div class="wrap header-inner"><a class="brand" href="{prefix}index.html">{LOGO}<span>CoastalNow</span></a><nav class="nav"><a href="{prefix}index.html">Home</a><a href="{prefix}index.html#states">States</a><a class="search-pill" href="{prefix}index.html#search">Search</a></nav></div></header><main class="wrap">{body}</main><footer><div class="wrap footer-inner"><strong>CoastalNow</strong><div class="footer-links"><a href="{prefix}methodology/index.html">Methodology</a><a href="{prefix}about/index.html">About</a><a href="{prefix}privacy/index.html">Privacy</a><a href="{prefix}contact/index.html">Contact</a></div></div></footer></body></html>'''

def _state_card(slug,items): return f'<a class="info-card state-card" href="tides/{slug}/index.html"><span class="state-code">{items[0]["state_code"]}</span><h3>{items[0]["state"]}</h3><p>{len(items)} coastal locations</p><span class="card-arrow">Browse state →</span></a>'

def _home(groups):
 all_items=sorted((x for v in groups.values() for x in v),key=lambda x:x['name'].casefold()); data=json.dumps([{'name':x['name'],'state':x['state'],'url':x['page_path'],'status':location_status(x)} for x in all_items],ensure_ascii=False)
 activities=enabled_activities()
 body=_hero('COASTAL TIDE DIRECTORY','Find tide times by coastal location.','Check today’s high and low tides, tide charts, 7-day schedules and coastal planning information from NOAA-based pages.')
 body+=f'''<section class="section" id="search"><div class="section-head"><h2>Find a beach or city</h2><p>Search {len(all_items)} coastal locations</p></div><div class="search-box"><input id="q" placeholder="San Diego, Florida, Holden Beach…"><button onclick="go()">Search</button></div><div id="results" class="directory-grid"></div></section>'''
 if activities:
  body+=f'''<section class="section" id="activities"><div class="section-head"><h2>Explore by activity</h2><p>Compare coastal conditions by what you want to do</p></div><div class="directory-grid">{"".join(_activity_card(item) for item in activities)}</div></section>'''
 body+=f'''<section class="section" id="states"><div class="section-head"><h2>Browse by state</h2><p>State directories</p></div><div class="directory-grid">{"".join(_state_card(k,v) for k,v in groups.items())}</div></section><section class="section"><div class="section-head"><h2>All coastal locations</h2><p>Live NOAA and Preview status</p></div><div class="directory-grid">{"".join(_card(x,x["page_path"]) for x in all_items)}</div></section><script>const L={data};function go(){{const q=document.getElementById('q').value.toLowerCase().trim();document.getElementById('results').innerHTML=q?L.filter(x=>(x.name+' '+x.state).toLowerCase().includes(q)).slice(0,12).map(x=>`<a class="info-card" href="${{x.url}}"><span class="status-badge ${{x.status==='Live NOAA'?'badge-live':'badge-preview'}}">${{x.status}}</span><h3>${{x.name}}</h3><p>${{x.state}}</p></a>`).join('')||'<p>No result</p>':''}}</script>'''
 return _shell('CoastalNow | Tide Times, Tide Charts & 7-Day Schedules','Check today’s high and low tide times, tide charts, 7-day tide schedules and coastal activity conditions for U.S. coastal locations with NOAA source details.','',body,'',[('Home','')])

def _state_location_section(title, items, helper_text=''):
 if not items: return ''
 copy=f'<p>{escape(helper_text)}</p>' if helper_text else f'<p>{len(items)} locations</p>'
 cards=''.join(_card(x,x['slug']+'/index.html') for x in items)
 return f'<section class="section"><div class="section-head"><h2>{escape(title)}</h2>{copy}</div><div class="directory-grid">{cards}</div></section>'

def _state_page(items):
 name=items[0]['state']; slug=items[0]['state_slug']; config=state_landing_config(slug)
 hero_copy=(config['intro'] if config else f'Browse {len(items)} coastal locations with the same clear status and page layout.')
 body=f'<div class="breadcrumbs"><a href="../../index.html">Home</a><span>/</span>{escape(name)}</div>'+_hero(f'{items[0]["state_code"]} DIRECTORY',f'{name} Tide Times',hero_copy)
 if config:
  body+=f'<section class="section"><article class="info-card"><p class="eyebrow">STATE TIDE GUIDE</p><h2>{escape(config["guide_title"])}</h2><p>{escape(config["intro"])}</p></article></section>'
  featured=items_for_slugs(items,config.get('featured',[]))
  body+=_state_location_section(config['featured_title'],featured,'Locations prioritized from current search response and expansion work')
  for region in config.get('regions',[]):
   members=state_region_items(slug,region['key'],items)
   body+=_state_location_section(region['title'],members,'Browse local tide times and 7-day schedules')
  body+=_state_location_section('All tide locations',items,f'{len(items)} coastal locations')
  desc=config['meta_description']
 else:
  body+=_state_location_section('Choose a coastal location',items,f'{len(items)} locations')
  desc=f'Browse tide pages for coastal locations in {name}.'
 path=f'tides/{slug}/index.html'
 return _shell(f'{name} Tide Times | CoastalNow',desc,'../../',body,path,[('Home',''),(name,path)])

def _trust_page(slug,title,description,eyebrow,hero_copy,content):
 path=f'{slug}/index.html'
 body=f'<div class="breadcrumbs"><a href="../index.html">Home</a><span>/</span>{escape(title)}</div>'
 body+=_hero(eyebrow,title,hero_copy)
 body+=f'<section class="section"><article class="info-card">{content}</article></section>'
 return _shell(title if title.endswith('CoastalNow') else f'{title} | CoastalNow',description,'../',body,path,[('Home',''),(title,path)])

def _about_page():
 content='''<p>CoastalNow is an independent coastal-information site built to make tide timing and coastal planning information easier to scan by location. Tide pages put the next high or low tide first, then show today’s tide chart and a 7-day schedule.</p><p>Tide predictions are sourced from NOAA/NOS/CO-OPS. Some locations use a nearby NOAA station when a location-specific station is not available; those pages identify the reference station and disclose the approximate distance. Activity pages may combine tide, wind, wave, weather and alert context using the rules described in the <a href="../methodology/index.html"><strong>CoastalNow methodology</strong></a>.</p><p>CoastalNow is not affiliated with NOAA, the National Weather Service or the U.S. government. Information is provided as a planning reference, and official warnings, closures, signs and local guidance should always take priority.</p>'''
 return _trust_page('about','About CoastalNow','Learn how CoastalNow presents NOAA tide predictions, coastal activity context, nearby-station disclosures and methodology.','ABOUT THE SERVICE','Clear tide information with visible sources and methodology.',content)

def _privacy_page():
 content='''<p>CoastalNow does not require a user account or an on-site contact form. Our hosting and security providers may process standard technical request information, such as IP address, browser information, requested URL and timestamps, as part of operating and protecting the site.</p><p>CoastalNow links to external services and data providers. Those services operate under their own privacy policies. If Google advertising services are enabled on CoastalNow, third-party vendors including Google may use cookies or similar technologies to serve and measure advertising, including personalized advertising where permitted.</p><p>You can review or change Google advertising preferences in <a href="https://adssettings.google.com/"><strong>Ads Settings</strong></a>. Where consent is required, a consent control may be shown before applicable advertising storage or personalization is used.</p><p>Questions about privacy or site data can be reported through the public contact route. Please do not post passwords, private account information or other sensitive personal information in a public issue. Last updated: September 2026.</p>'''
 return _trust_page('privacy','Privacy','Read CoastalNow privacy information, including technical logs, external services and Google advertising cookie disclosures.','PRIVACY','How CoastalNow handles site operation data and advertising-related disclosures.',content)

def _contact_page():
 content='''<p>For a tide-data correction, broken page, source question or general site feedback, open an issue in the <a href="https://github.com/hmx112/coastalnow/issues"><strong>CoastalNow public issue tracker</strong></a>.</p><p>For a data correction, include the CoastalNow page URL, the location name and a short description of what appears incorrect. If the question is about a NOAA station or nearby-station disclosure, include that detail as well.</p><p>Privacy questions can also be raised through the issue tracker, but the tracker is public. Do not include sensitive personal information, account credentials or anything you would not want published publicly.</p>'''
 return _trust_page('contact','Contact CoastalNow','Contact CoastalNow about tide data corrections, broken pages, source questions, privacy or general site feedback.','CONTACT','A public route for corrections, source questions and site feedback.',content)

def build_directory_pages():
 g=_groups()
 pages={'index.html':_home(g),**{f'tides/{k}/index.html':_state_page(v) for k,v in g.items()}}
 pages.update({
  'about/index.html':_about_page(),
  'privacy/index.html':_privacy_page(),
  'contact/index.html':_contact_page(),
 })
 return pages
