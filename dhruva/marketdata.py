"""Append-only daily updates of the index and ETF series the paper books use.

Existing rows are never overwritten; a later vendor revision is logged instead,
so the forward record cannot drift silently.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data'/'indices'
NSE = {'NIFTY_50': 'NIFTY 50', 'NIFTY200_MOMENTUM_30': 'NIFTY200 MOMENTUM 30',
       'NIFTY_MIDCAP150_MOMENTUM_50': 'NIFTY MIDCAP150 MOMENTUM 50'}
UA = 'Mozilla/5.0'


def nse_tri(name, start, end):
    body = json.dumps({'cinfo': "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" % (
        name, start.strftime('%d-%b-%Y'), end.strftime('%d-%b-%Y'), name)}).encode()
    req = urllib.request.Request('https://www.niftyindices.com/BackPage/getTotalReturnIndexString', data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8', 'User-Agent': UA})
    for attempt in range(4):
        try:
            rows = json.load(urllib.request.urlopen(req, timeout=60))
            return pd.Series({pd.Timestamp(datetime.strptime(r['Date'], '%d %b %Y')): float(str(r['TotalReturnsIndex']).replace(',', ''))
                              for r in rows})
        except Exception as exc:
            error = exc; time.sleep(3*(attempt+1))
    raise RuntimeError(f'NSE {name}: {type(error).__name__}')


def yahoo_close(symbol, rng='1mo'):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol, safe="")}?range={rng}&interval=1d'
    for attempt in range(4):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30))['chart']['result'][0]
            s = pd.Series(r['indicators']['quote'][0]['close'], index=pd.to_datetime(r['timestamp'], unit='s').normalize())
            return s.dropna()[lambda x: ~x.index.duplicated(keep='last')]
        except Exception as exc:
            error = exc; time.sleep(2*(attempt+1))
    raise RuntimeError(f'Yahoo {symbol}: {type(error).__name__}')


def merge(file, fresh, through):
    """Append rows after the last saved date, up to `through`. Returns (added, revisions)."""
    path = DATA/(file+'.csv')
    old = pd.read_csv(path, index_col='date', parse_dates=True)['tri']
    fresh = fresh[fresh.index <= pd.Timestamp(through)].dropna()
    common = fresh.index.intersection(old.index)
    revisions = [str(d.date()) for d in common if abs(fresh[d]/old[d]-1) > 1e-4]
    new = fresh[fresh.index > old.index.max()]
    if len(new):
        pd.concat([old, new]).rename('tri').to_csv(path, index_label='date')
    return len(new), revisions


def update(through):
    """Fetch every series up to the completed session `through` (ISO date)."""
    end = date.fromisoformat(through); start = end-timedelta(days=20)
    report = {}
    for file, name in NSE.items():
        report[file] = merge(file, nse_tri(name, start, end), through)
    report['GOLDBEES'] = merge('GOLDBEES', yahoo_close('GOLDBEES.NS'), through)
    ndx, inr = yahoo_close('^NDX'), yahoo_close('INR=X')
    inr = inr.reindex(ndx.index.union(inr.index)).ffill()
    report['NASDAQ100_INR'] = merge('NASDAQ100_INR', (ndx*inr.reindex(ndx.index)).dropna(), through)
    return {k: {'added': a, 'revisions_ignored': r} for k, (a, r) in report.items()}


def latest(file):
    return str(pd.read_csv(DATA/(file+'.csv'), usecols=['date'])['date'].max())[:10]
