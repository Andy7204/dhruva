"""Evaluate every pre-registered candidate. Writes research/v2/results/.

    python research/v2/run.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E  # noqa: E402
import strategies as S  # noqa: E402

OUT = HERE/'results'
HOLDOUT = '2016-01-01'


def evaluate(prices, name, factory, start, end):
    strat = factory(); strat.start = start
    curve, acct, _ = E.run(prices, strat, start, end)
    return curve, acct


def rolling(curve, bench, years):
    n = int(252*years)
    a, b = curve.values, bench.reindex(curve.index).values
    rows = [((a[i+n]/a[i])**(1/years)-1, (b[i+n]/b[i])**(1/years)-1) for i in range(0, len(a)-n, 5)]
    if not rows: return None
    ex = np.array([x-y for x, y in rows])
    return {'windows': len(rows), 'beat_pct': round(float((ex > 0).mean()*100), 1),
            'median_excess_pct': round(float(np.median(ex)*100), 2),
            'worst_excess_pct': round(float(ex.min()*100), 2),
            'median_cagr_pct': round(float(np.median([x for x, _ in rows])*100), 2)}


def main():
    OUT.mkdir(exist_ok=True)
    prices = E.load()
    needed = sorted({a for f in S.CANDIDATES.values() for a in _assets(f)} | {'LIQ', 'N50'})
    first = max(prices[a].first_valid_index() for a in needed)
    start = prices.index.get_indexer([first+pd.Timedelta(days=366)], method='bfill')[0]
    end = len(prices)-1
    split = prices.index.get_indexer([pd.Timestamp(HOLDOUT)], method='bfill')[0]
    rf = prices['LIQ']
    results, curves = {}, {}
    for name, factory in S.CANDIDATES.items():
        print(name, flush=True)
        full, acct = evaluate(prices, name, factory, start, end)
        design, _ = evaluate(prices, name, factory, start, split)
        hold, _ = evaluate(prices, name, factory, split, end)
        curves[name] = full['liq']
        uses = [a for a in _assets(factory) if a in E.LAUNCH]
        live_from = max([E.LAUNCH[a] for a in uses] or ['2007-10-01'])
        li = prices.index.get_indexer([pd.Timestamp(live_from)], method='bfill')[0]
        live, _ = evaluate(prices, name, factory, max(li, start), end) if end-li > 252 else (None, None)
        bench_live, _ = evaluate(prices, 'bench', S.CANDIDATES['Nifty 50 buy and hold (benchmark)'], max(li, start), end) if live is not None else (None, None)
        results[name] = {'full': E.metrics(full['liq'], rf), 'design': E.metrics(design['liq'], rf),
                         'holdout': E.metrics(hold['liq'], rf), 'tax_paid': round(acct.tax_paid),
                         'costs': round(acct.costs), 'trades': acct.trades, 'live_from': live_from,
                         'live': E.metrics(live['liq'], rf) if live is not None else None,
                         'live_benchmark': E.metrics(bench_live['liq'], rf) if live is not None else None}
    bench = curves['Nifty 50 buy and hold (benchmark)']
    for name in results:
        results[name]['rolling'] = {f'{y}y': rolling(curves[name], bench, y) for y in (3, 5, 10)}
    meta = {'window': [str(prices.index[start].date()), str(prices.index[end].date())],
            'holdout_from': HOLDOUT, 'candidates': len(S.CANDIDATES), 'capital': 1_000_000,
            'basis': 'liquidation value after ETF costs and Indian tax; one-day execution lag'}
    (OUT/'results.json').write_text(json.dumps({'meta': meta, 'results': results}, indent=1))
    pd.DataFrame(curves).to_csv(OUT/'curves.csv')
    rows = []
    for name, r in results.items():
        f, h, d = r['full'], r['holdout'], r['design']
        rows.append([name, f['cagr_pct'], f['max_dd_pct'], f['sharpe'], f['sortino'], f['calmar'],
                     d['cagr_pct'], h['cagr_pct'], (r['rolling']['5y'] or {}).get('beat_pct'),
                     (r['rolling']['10y'] or {}).get('beat_pct'), r['live_from'],
                     (r['live'] or {}).get('cagr_pct'), (r['live_benchmark'] or {}).get('cagr_pct')])
    table = pd.DataFrame(rows, columns=['strategy', 'CAGR', 'maxDD', 'Sharpe', 'Sortino', 'Calmar',
                                        'design CAGR', 'holdout CAGR', 'beat 5y %', 'beat 10y %',
                                        'live from', 'live CAGR', 'Nifty50 same period'])
    table.sort_values('CAGR', ascending=False).to_csv(OUT/'scorecard.csv', index=False)
    print(meta)
    print(table.sort_values('CAGR', ascending=False).to_string(index=False))


def _assets(factory):
    import inspect
    src = inspect.getsource(factory)
    return [a for a in E.ASSETS if f"'{a}'" in src] + (S.FACTORS if 'FACTORS' in src else [])


if __name__ == '__main__':
    main()
