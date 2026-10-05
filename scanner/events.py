"""Event engine: read material NSE filings, extract numbers, decide the fast lane.

Only filings with quantities can move a score; press releases about products
cannot. Every fired signal is logged with its date and price so its forward
precision can be measured later (scanner/audit.py), which is how new rules are
kept honest.
"""
import hashlib
import io
import json
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'data'/'scanner_cache'/'pdf_text'
SIGNALS = ROOT/'runs'/'inflection'/'signals.jsonl'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'
MAX_NEW_PDFS = 400  # per run; the backlog is finished on later runs, newest filings first
_budget = {'left': MAX_NEW_PDFS}
import logging
logging.getLogger('pypdf').setLevel(logging.ERROR)

ORDER, CAPACITY, PRODUCTION = 'Bagging/Receiving of orders/contracts', 'Capacity addition', 'Commencement of commercial production/operations'
PREFERENTIAL, QIP = 'Preferential issue', 'Qualified Institutional Placement'
SURVEILLANCE = ('Price movement', 'Spurt in Volume')
READ = (ORDER, CAPACITY, PRODUCTION, PREFERENTIAL, QIP)
RATING_PREFIX = 'Credit Rating'

# Fast-lane thresholds (pre-registered 2026-10-03; change only with a dated note in docs/ARCHITECTURE_V3.md)
FAST = {'order_intensity': 0.20, 'capacity_pct': 25, 'promoter_pct_mcap': 3.0, 'promoter_price_ratio': 0.90,
        'weekly_cap': 5}

UNITS = {'crore': 1, 'crores': 1, 'cr': 1, 'cr.': 1, 'lakh': 0.01, 'lakhs': 0.01, 'lac': 0.01, 'lacs': 0.01,
         'million': 0.1, 'mn': 0.1, 'billion': 100, 'bn': 100}
AMOUNT = re.compile(r'(USD|US\$|\$|INR|Rs\.?|₹)\s*~?\s*([\d][\d,]*(?:\.\d+)?)\s*(crores?|cr\.?|lakhs?|lacs?|million|mn|billion|bn)?\b', re.I)


def pdf_text(url, max_pages=12):
    """Download and cache the text of a filing PDF (first pages only)."""
    if not url or not url.lower().endswith('.pdf'):
        return ''
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE/(hashlib.sha1(url.encode()).hexdigest()+'.txt')
    if path.exists():
        return path.read_text(encoding='utf-8')
    if _budget['left'] <= 0:
        return None  # not read yet this run
    _budget['left'] -= 1
    from pypdf import PdfReader
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60).read()
        text = '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(raw)).pages[:max_pages])
    except Exception:
        text = ''
    path.write_text(text, encoding='utf-8')
    time.sleep(0.3)
    return text


def amounts(text, usd_inr):
    """All money amounts in INR crore, with their position in the text."""
    out = []
    for m in AMOUNT.finditer(text):
        cur, num, unit = m.group(1).upper(), m.group(2).replace(',', ''), (m.group(3) or '').lower()
        try:
            value = float(num)
        except ValueError:
            continue
        if cur in ('USD', 'US$', '$'):
            if unit not in ('million', 'mn', 'billion', 'bn'):
                continue  # bare dollar figures are usually unit prices
            value = value*(1000 if unit in ('billion', 'bn') else 1)*usd_inr/10  # USD million -> INR crore
        else:
            if not unit:
                if value < 1e5: continue  # plain rupees below 1 lakh are prices, not contract sizes
                value = value/1e7
            else:
                value *= UNITS.get(unit, 1)
        out.append((m.start(), value))
    return out


def order_facts(text, usd_inr):
    t = ' '.join(text.split())
    low = t.lower()
    found = amounts(t, usd_inr)
    value = None
    for key in ('size of order', 'size of the order', 'value of order', 'order value', 'contract value', 'total potential value',
                'consideration', 'size', 'value', 'worth'):
        i = low.find(key)
        if i >= 0:
            near = [v for pos, v in found if i <= pos <= i+400]
            if near:
                value = near[0]; break
    if value is None and found:
        value = max(v for _, v in found)
    years = None
    m = re.search(r'(?:FY|CY)\s?(\d{2,4})\s*(?:to|-|–)\s*(?:FY|CY)?\s?(\d{2,4})', t)
    if m:
        a, b = int(m.group(1)[-2:]), int(m.group(2)[-2:])
        years = max(1, b-a+1)
    m2 = re.search(r'(?:over|within|period of|tenure of)\s+(?:a period of\s+)?(\d{1,2})\s*(?:years|yrs)', low)
    if m2: years = int(m2.group(1))
    m3 = re.search(r'(?:within|period of|over)\s+(\d{1,2})\s*months', low)
    if not years and m3: years = max(1, int(m3.group(1))/12)
    firm = 1.0
    if any(k in low for k in ('potential value', 'allocation', 'letter of intent', ' loi', 'award letter', 'framework agreement', 'mou')):
        firm = 0.5
    elif 'purchase order' in low or 'work order' in low:
        firm = 1.0
    # NSE's annexure template always contains the words "domestic/international entity";
    # read the answer that follows it instead of the question.
    customer = 'domestic'
    i = low.find('international entity')
    answer = low[i+20:i+120] if i >= 0 else ''
    if any(k in low for k in ('hyperscale', 'overseas')) or ('international' in answer and 'domestic' not in answer[:40]):
        customer = 'international'
    tier1 = any(k in low for k in ('hyperscale', 'fortune', 'global tier', 'tier-1', 'tier 1', 'oem'))
    return {'value_cr': round(value, 2) if value else None, 'years': years, 'firmness': firm,
            'customer': customer, 'tier1_customer': tier1}


def capacity_facts(text, usd_inr):
    low = ' '.join(text.split()).lower()
    pct = re.search(r'(\d{1,3})\s*%\s*(?:increase|addition|expansion|enhancement|higher)', low)
    util = re.search(r'utili[sz]ation[^\d]{0,40}(\d{1,3})\s*%', low)
    capex = [v for _, v in amounts(' '.join(text.split()), usd_inr)]
    return {'capacity_pct': int(pct.group(1)) if pct else None, 'utilization_pct': int(util.group(1)) if util else None,
            'capex_cr': round(max(capex), 2) if capex else None}


def preferential_facts(text, usd_inr):
    t = ' '.join(text.split()); low = t.lower()
    price = re.search(r'(?:price|issue price)[^₹\d]{0,60}(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)', t, re.I)
    size = [v for _, v in amounts(t, usd_inr) if v > 1]
    return {'promoter': 'promoter' in low, 'price': float(price.group(1).replace(',', '')) if price else None,
            'size_cr': round(max(size), 2) if size else None, 'warrants': 'warrant' in low}


def rating_facts(text):
    low = ' '.join(text.split()).lower()
    if 'upgrad' in low: move = 1
    elif 'downgrad' in low: move = -1
    elif 'outlook' in low and 'positive' in low and 'revised' in low: move = 0.5
    elif 'outlook' in low and 'negative' in low and 'revised' in low: move = -0.5
    else: move = 0
    return {'rating_move': move}


def evaluate(filings, fund, prices, usd_inr, universe=None):
    """Return a DataFrame of extracted events with materiality and fast-lane flags."""
    def ttm_revenue(sym):
        q = [v for _, v in (fund.get(sym) or {}).get('quarterlyTotalRevenue', [])]
        return sum(q[-4:])/1e7 if len(q) >= 4 else None

    def mcap(sym):
        f = fund.get(sym) or {}
        sh = [v for _, v in f.get('quarterlyOrdinarySharesNumber', []) or f.get('annualOrdinarySharesNumber', [])]
        px = prices.get(sym)
        return (float(px['close'].iloc[-1])*sh[-1]/1e7) if sh and px is not None and len(px) else None

    def close_on(sym, day):
        px = prices.get(sym)
        if px is None or not len(px): return None
        s = px['close'].loc[:pd.Timestamp(day)]
        return float(s.iloc[-1]) if len(s) else None

    rows = []
    filings = sorted(filings, key=lambda a: str(a.get('time')), reverse=True)  # newest first
    for a in filings:
        desc, sym = a.get('desc') or '', a.get('symbol')
        if universe is not None and sym not in universe: continue
        if not (desc in READ or desc.startswith(RATING_PREFIX)): continue
        day = str(a.get('time'))[:10]
        text = pdf_text(a.get('url'))
        if text is None: continue  # deferred to a later run by the PDF budget
        text = text or a.get('text', '')
        rev, cap = ttm_revenue(sym), mcap(sym)
        row = {'date': day, 'symbol': sym, 'desc': desc, 'url': a.get('url'), 'price': close_on(sym, day),
               'ttm_revenue_cr': round(rev, 1) if rev else None, 'mcap_cr': round(cap, 1) if cap else None}
        why = []
        if desc == ORDER:
            f = order_facts(text, usd_inr); row.update(f)
            if f['value_cr'] and rev:
                annual = f['value_cr']/(f['years'] or 1)
                row['order_intensity'] = round(annual*f['firmness']/rev, 3)
                if row['order_intensity'] >= FAST['order_intensity']: why.append(f"order ≈{row['order_intensity']*100:.0f}% of annual revenue (after firmness haircut)")
            if f['tier1_customer']: why.append('global Tier-1/hyperscale customer')
        elif desc == CAPACITY:
            f = capacity_facts(text, usd_inr); row.update(f)
            if (f['capacity_pct'] or 0) >= FAST['capacity_pct']: why.append(f"capacity +{f['capacity_pct']}%")
            if f['capex_cr'] and cap and f['capex_cr'] >= 0.3*cap: why.append('capex ≥30% of market cap')
        elif desc == PRODUCTION:
            row['commissioning'] = True
        elif desc == PREFERENTIAL:
            f = preferential_facts(text, usd_inr); row.update(f)
            if f['promoter'] and f['size_cr'] and cap:
                row['promoter_pct_mcap'] = round(f['size_cr']/cap*100, 2)
                ratio = (f['price']/row['price']) if f['price'] and row['price'] else None
                row['price_ratio'] = round(ratio, 2) if ratio else None
                if row['promoter_pct_mcap'] >= FAST['promoter_pct_mcap'] and (ratio or 0) >= FAST['promoter_price_ratio']:
                    why.append(f"promoter puts in {row['promoter_pct_mcap']}% of market cap at {ratio:.0%} of market price")
        elif desc == QIP:
            row['dilution_event'] = True
        elif desc.startswith(RATING_PREFIX):
            f = rating_facts(text); row.update(f)
            if f['rating_move'] >= 1: why.append('credit rating upgrade')
        row['fast_lane_reasons'] = '; '.join(why)
        row['material'] = bool(why)
        rows.append(row)
    return pd.DataFrame(rows)


def surveillance_join(filings, events, window=3):
    """Exchange price/volume queries within +-window days of a material event: research trigger only."""
    if events is None or not len(events): return set()
    mat = events[events['material']]
    flags = {}
    for a in filings:
        if a.get('desc') in SURVEILLANCE:
            flags.setdefault(a['symbol'], []).append(pd.Timestamp(str(a.get('time'))[:10]))
    hit = set()
    for _, e in mat.iterrows():
        d = pd.Timestamp(e['date'])
        if any(abs((x-d).days) <= window for x in flags.get(e['symbol'], [])): hit.add(e['symbol'])
    return hit


def log_signals(events, session):
    """Append newly seen material events to the permanent signal log (for forward precision)."""
    SIGNALS.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if SIGNALS.exists():
        for line in SIGNALS.read_text(encoding='utf-8').splitlines():
            r = json.loads(line); seen.add((r['symbol'], r['date'], r['desc']))
    new = []
    for _, e in events[events['material']].iterrows() if len(events) else []:
        key = (e['symbol'], e['date'], e['desc'])
        if key in seen: continue
        new.append({'symbol': e['symbol'], 'date': e['date'], 'desc': e['desc'], 'price': e['price'],
                    'reasons': e['fast_lane_reasons'], 'logged_on': session})
    with SIGNALS.open('a', encoding='utf-8') as f:
        for r in new: f.write(json.dumps(r, sort_keys=True)+'\n')
    return new
