"""Robustness of the leading candidates: review-date offsets and doubled costs."""
import json, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E, strategies as S

TOP = ['Accelerating dual momentum (Mom30, Midcap Mom50, Nasdaq-100, gold)',
       'Midcap Momentum 50 70% + Gold 30%, yearly',
       'Momentum 30 60% + Gold 20% + Nasdaq-100 20%, yearly',
       'Midcap150 Momentum 50 buy and hold', 'Alpha 50 buy and hold',
       'Nifty 50 buy and hold (benchmark)']


def main():
    p = E.load(); end = len(p)-1
    base = p.index.get_indexer([pd.Timestamp('2007-10-01')], method='bfill')[0]
    out = {}
    for name in TOP:
        row = {}
        for off in (0, 5, 10, 15):
            st = S.CANDIDATES[name](); st.start = base+off
            c, _, _ = E.run(p, st, base+off, end)
            row[f'offset_{off}'] = E.metrics(c['liq'])['cagr_pct']
        saved = dict(E.ASSETS)
        for a, v in saved.items(): E.ASSETS[a] = (v[0], v[1], v[2], v[3]*2)
        st = S.CANDIDATES[name](); st.start = base
        c, _, _ = E.run(p, st, base, end)
        E.ASSETS.update(saved)
        row['double_costs'] = E.metrics(c['liq'])['cagr_pct']
        out[name] = row; print(name, row, flush=True)
    (HERE/'results/robustness.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
