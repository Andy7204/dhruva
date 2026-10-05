"""Inputs for the multibagger scanner: universe, prices, fundamentals, announcements.

Caches live in data/scanner_cache/ (not committed; the workflow restores them
with actions/cache). Every fetch failure is recorded, never silently treated as
a zero.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
import csv
import io
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'data'/'scanner_cache'
UNIVERSE = ROOT/'data'/'universe.csv'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'
Q = ['TotalRevenue', 'EBITDA', 'NormalizedEBITDA', 'TotalUnusualItems', 'PretaxIncome', 'TaxProvision',
     'InterestExpense', 'NetIncome', 'GrossProfit', 'DilutedEPS', 'OrdinarySharesNumber',
     'OperatingIncome', 'ReconciledDepreciation', 'OtherNonOperatingIncomeExpenses']
A = ['OperatingCashFlow', 'CapitalExpenditure', 'FreeCashFlow', 'AccountsReceivable', 'Inventory', 'AccountsPayable',
     'CashAndCashEquivalents', 'NetDebt', 'TotalDebt', 'OrdinarySharesNumber', 'EBITDA', 'TotalRevenue', 'NetIncome',
     'InvestedCapital', 'StockholdersEquity', 'InterestExpense', 'DilutedEPS']
FUNDAMENTALS = ','.join(['quarterly'+x for x in Q]+['annual'+x for x in A])


def _get(url, headers=None, timeout=30, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as exc:
            error = exc; time.sleep(1.5*(attempt+1))
    raise RuntimeError(f'{type(error).__name__}: {error}')


def refresh_universe():
    """All NSE main-board (EQ) equities; industry from the official Nifty Total Market list where available.

    Names that leave the list are kept in data/universe_log.csv (point-in-time record).
    """
    raw = _get('https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv').decode('utf-8-sig')
    rows = [{k.strip(): (v or '').strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(raw))]
    # BE (trade-for-trade) included: NSE moves stocks there after explosive moves (e.g. STLTECH in 2026).
    eq = [r for r in rows if r.get('SERIES') in ('EQ', 'BE') and r.get('SYMBOL')]
    if len(eq) < 1500:
        raise RuntimeError(f'NSE equity list too short: {len(eq)}')
    industry = {}
    try:
        tm = _get('https://www.niftyindices.com/IndexConstituent/ind_niftytotalmarket_list.csv').decode('utf-8-sig')
        industry = {r['Symbol'].strip(): r['Industry'].strip() for r in csv.DictReader(io.StringIO(tm)) if r.get('Symbol')}
    except Exception:
        pass
    old = pd.read_csv(UNIVERSE) if UNIVERSE.exists() else pd.DataFrame(columns=['symbol', 'name', 'industry'])
    known = dict(zip(old['symbol'], old['industry']))
    frame = pd.DataFrame({'symbol': [r['SYMBOL'] for r in eq], 'name': [r['NAME OF COMPANY'] for r in eq], 'series': [r['SERIES'] for r in eq],
                          'industry': [industry.get(r['SYMBOL']) or (known.get(r['SYMBOL']) if known.get(r['SYMBOL']) != 'Unclassified' else None)
                                       or 'Unclassified' for r in eq]})
    added, removed = set(frame['symbol'])-set(old['symbol']), set(old['symbol'])-set(frame['symbol'])
    if (added or removed) and len(old):
        log = ROOT/'data'/'universe_log.csv'
        stamp = date.today().isoformat()
        lines = [f'{stamp},added,{s}' for s in sorted(added)]+[f'{stamp},removed,{s}' for s in sorted(removed)]
        new_file = not log.exists()
        with log.open('a', encoding='utf-8') as f:
            if new_file: f.write('date,change,symbol\n')
            f.write('\n'.join(lines)+'\n')
    frame.to_csv(UNIVERSE, index=False)
    return frame


def universe():
    return pd.read_csv(UNIVERSE)


def _yahoo_chart(symbol, rng):
    r = json.loads(_get(f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={rng}&interval=1d'))['chart']['result'][0]
    q = r['indicators']['quote'][0]
    f = pd.DataFrame({k: q[k] for k in ('open', 'high', 'low', 'close', 'volume')},
                     index=pd.to_datetime(r['timestamp'], unit='s').normalize())
    return f.dropna(subset=['close'])[lambda x: ~x.index.duplicated(keep='last')]


def prices(symbols, through):
    """Daily OHLCV per symbol through `through`; 2y cold start, 1mo incremental."""
    folder = CACHE/'prices'; folder.mkdir(parents=True, exist_ok=True)
    errors = {}

    def one(sym):
        path = folder/(sym.replace('^', '_').replace('&', '_')+'.csv')
        try:
            old = pd.read_csv(path, index_col=0, parse_dates=True) if path.exists() else None
            fresh = _yahoo_chart(sym, '1mo' if old is not None and len(old) > 200 else '2y')
            frame = fresh if old is None else pd.concat([old[old.index < fresh.index.min()], fresh])
            frame = frame[frame.index <= pd.Timestamp(through)]
            frame.to_csv(path)
            return sym, frame
        except Exception as exc:
            errors[sym] = str(exc)
            return sym, (pd.read_csv(path, index_col=0, parse_dates=True) if path.exists() else None)
    with ThreadPoolExecutor(6) as pool:
        out = dict(pool.map(one, symbols))
    return {k: v for k, v in out.items() if v is not None and len(v)}, errors


def fundamentals(symbols, max_age_days=6):
    """Yahoo fundamentals time series, refreshed weekly per symbol."""
    folder = CACHE/'fundamentals'; folder.mkdir(parents=True, exist_ok=True)
    errors = {}
    now = time.time()

    def one(sym):
        path = folder/(sym+'.json')
        if path.exists() and now-path.stat().st_mtime < max_age_days*86400:
            return sym, json.loads(path.read_text())
        try:
            end = int(now); raw = json.loads(_get(
                f'https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{sym}'
                f'?type={FUNDAMENTALS}&period1=1500000000&period2={end}'))
            data = {}
            for x in raw['timeseries']['result']:
                k = x['meta']['type'][0]
                data[k] = [[v['asOfDate'], v['reportedValue']['raw']] for v in x.get(k, []) if v and v.get('reportedValue')]
            path.write_text(json.dumps(data))
            return sym, data
        except Exception as exc:
            errors[sym] = str(exc)
            return sym, (json.loads(path.read_text()) if path.exists() else None)
    with ThreadPoolExecutor(6) as pool:
        out = dict(pool.map(one, symbols))
    return {k: v for k, v in out.items() if v}, errors


def announcements(through, days=120):
    """NSE corporate announcements for the last `days`, cached per week."""
    folder = CACHE/'announcements'; folder.mkdir(parents=True, exist_ok=True)
    end = date.fromisoformat(through); start = end-timedelta(days=days)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    try:
        opener.open(urllib.request.Request('https://www.nseindia.com/', headers={'User-Agent': UA}), timeout=30)
    except Exception:
        pass  # a 403 homepage still sets the cookies the API needs
    rows, errors = [], []
    day = start
    while day <= end:
        stop = min(day+timedelta(days=6), end)
        path = folder/f'{day.isoformat()}_{stop.isoformat()}.json'
        final = stop < end-timedelta(days=3)  # recent weeks are re-fetched as filings arrive
        if final and path.exists():
            rows += json.loads(path.read_text(encoding='utf-8'))
        else:
            url = (f'https://www.nseindia.com/api/corporate-announcements?index=equities'
                   f'&from_date={day:%d-%m-%Y}&to_date={stop:%d-%m-%Y}')
            try:
                req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://www.nseindia.com/'})
                data = json.loads(opener.open(req, timeout=60).read())
                slim = [{'symbol': a.get('symbol'), 'desc': a.get('desc'), 'text': (a.get('attchmntText') or '')[:300],
                         'time': a.get('sort_date') or a.get('an_dt'), 'url': a.get('attchmntFile')} for a in data]
                path.write_text(json.dumps(slim), encoding='utf-8')
                rows += slim
            except Exception as exc:
                errors.append(f'{day}: {type(exc).__name__}')
                if path.exists(): rows += json.loads(path.read_text(encoding='utf-8'))
            time.sleep(0.5)
        day = stop+timedelta(days=1)
    return rows, errors
