"""Longer-window rerun of the challenge study plus a survivorship control.

Added September29, 2026 at the owner's request. Reuses research/challenge.py
unchanged; only the price source differs (up to 20 years of Yahoo daily bars in
research/long/data/cache, which is not committed). Never touches production.

    python research/long_window.py --fetch   # download, once
    python research/long_window.py           # run, writes research/results/long_window.json

Point-in-time index membership is not freely available and Yahoo has no prices
for delisted companies, so survivorship bias cannot be removed. Instead the
survivor control buys every stock in today's list at the start, equal weight,
and holds it. That basket enjoys the same hindsight as Dhruva's universe, so
Dhruva's margin over it, not over Nifty, is the part that survivorship cannot explain.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LONG = HERE / 'long'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from qlab import data as D, costs as C  # noqa: E402

RANGE = '20y'
VARIANTS = ['current_200_63', 'faster_100_63', 'no_market_gate_63', 'core_plus_index', 'index_hold']


def fetch():
    cfg = D.load_config()
    symbols = list(dict.fromkeys(cfg['universe'] + ['NIFTYBEES.NS', '^NSEI']))
    folder = LONG / 'data/cache'; folder.mkdir(parents=True, exist_ok=True)
    (LONG/'data/nifty100.txt').write_text((ROOT/'data/nifty100.txt').read_text())
    failed = []
    for n, s in enumerate(symbols, 1):
        path = folder / (D._safe_name(s)+'.csv')
        if path.exists():
            continue
        try:
            D.fetch_yahoo(s, rng=RANGE).to_csv(path)
        except Exception as exc:
            failed.append(f'{s}: {type(exc).__name__}')
        if n % 50 == 0:
            print(f'{n}/{len(symbols)} fetched', flush=True)
        time.sleep(0.3)
    print(json.dumps({'symbols': len(symbols), 'failed': failed}), flush=True)


def survivor_basket(m, start, end, universe, cost_cfg):
    """Equal-weight buy-and-hold of every listed stock with a price at start."""
    allowed = m.stock_set if universe == '500' else m.stock_set & m.n100
    names = [s for s in sorted(allowed) if m.px(s, start) is not None]
    w = 100000/len(names)
    units = {s: (w - C.order_cost(w, 'buy', s, 'delivery', cost_cfg))/m.px(s, start) for s in names}
    nav = pd.Series({m.cal[i]: sum(u*m.mark(s, i) for s, u in units.items()) for i in range(start, end+1)})
    days = (m.cal[end]-m.cal[start]).days
    return {'return_pct': round((nav.iloc[-1]/100000-1)*100, 3),
            'cagr_pct': round(((nav.iloc[-1]/100000)**(365.25/days)-1)*100, 3),
            'max_drawdown_pct': round(float((nav/nav.cummax()-1).min()*100), 3),
            'stocks': len(names), 'note': 'pre-tax, buy cost only, no rebalancing'}


def main():
    import challenge
    challenge.ROOT = LONG  # Market reads ROOT/data/cache and ROOT/data/nifty100.txt
    cfg = D.load_config()
    m = challenge.Market(cfg)
    # Start once the NIFTYBEES benchmark itself has prices, after the usual warmup.
    etf_first = m.cal.get_loc(m.cols['adjclose']['NIFTYBEES.NS'].first_valid_index())
    start, end = max(260, etf_first+1), len(m.cal)-1
    out = {'window': [str(m.cal[start].date()), str(m.cal[end].date())], 'sessions': end-start+1,
           'symbols_with_data': len(m.symbols), 'range_requested': RANGE,
           'cache_sha256': hashlib.sha256(''.join(a.get('sha256', '') for a in m.audit.values()).encode()).hexdigest(),
           'full': {}, 'survivor_control': {}, 'by_period': {}}
    for universe in ['500', '100']:
        for name in VARIANTS:
            print('Long window', universe, name, flush=True)
            out['full'][f'{universe}/{name}'] = challenge.Trial(m, name, start, end, universe).run().summary()
        out['survivor_control'][universe] = survivor_basket(m, start, end, universe, cfg['costs'])
    # Fresh accounts per era, same rules, to show whether the edge is concentrated in one period.
    cuts = [start] + [i for i in range(start+1, end) if m.cal[i].year != m.cal[i-1].year and m.cal[i].year % 4 == 2] + [end]
    for a, b in zip(cuts, cuts[1:]):
        if b-a < 252:
            continue
        label = f'{m.cal[a].date()}..{m.cal[b].date()}'
        out['by_period'][label] = {name: challenge.Trial(m, name, a, b).run().summary()
                                   for name in ['current_200_63', 'index_hold']}
        out['by_period'][label]['survivor_500'] = survivor_basket(m, a, b, '500', cfg['costs'])
    (HERE/'results/long_window.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps({k: {n: (v.get('cagr_pct'), v.get('max_drawdown_pct')) for n, v in out[k].items()}
                      if k == 'full' else out[k] for k in ('window', 'full', 'survivor_control')}, indent=1))


if __name__ == '__main__':
    fetch() if '--fetch' in sys.argv else main()
