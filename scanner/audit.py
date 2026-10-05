"""Missed-winner audit and signal precision (docs/ARCHITECTURE_V3.md sections H-I).

1. Detect stocks whose return beat the Nifty 500 by >=20% in 1 month, >=40% in
   3 months or >=75% in 6 months.
2. For each, check what Dhruva saw *before* the move from its own dated logs
   (score history, fast-lane tickets, positions, signal log) and classify the
   failure: not in universe / not eligible / signal absent / below threshold /
   researched but no starter / caught.
3. Measure forward precision of every signal type over all logged firings,
   so a rule learned from one winner is judged on every stock it fires for,
   not just the winner (the control group).
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INF = ROOT/'runs'/'inflection'
AUDIT = INF/'audit'
WINDOWS = {21: 0.20, 63: 0.40, 126: 0.75}


def benchmark():
    s = pd.read_csv(ROOT/'data/indices/NIFTY_500.csv', index_col='date', parse_dates=True)['tri']
    return s[~s.index.duplicated()].sort_index()


def movers(frames, session):
    bench = benchmark()
    out = []
    for sym, f in frames.items():
        c = f['close'].loc[:pd.Timestamp(session)]
        if len(c) < 130: continue
        for n, threshold in WINDOWS.items():
            start = c.index[-n-1]
            b = bench.loc[:start]
            if not len(b): continue
            excess = (c.iloc[-1]/c.iloc[-n-1]-1)-(bench.loc[:c.index[-1]].iloc[-1]/b.iloc[-1]-1)
            if excess >= threshold:
                out.append({'symbol': sym, 'window_sessions': n, 'move_start': str(start.date()), 'start_price': round(float(c.iloc[-n-1]), 2),
                            'end_price': round(float(c.iloc[-1]), 2), 'excess_return_pct': round(excess*100, 1)}); break
    return pd.DataFrame(out)


def _history():
    p = INF/'score_history.csv'
    return pd.read_csv(p) if p.exists() else pd.DataFrame(columns=['date', 'symbol', 'score', 'discovery'])


def diagnose(row, universe_syms, hist, signals, transitions):
    """Why did (or didn't) Dhruva get there before the move started? Uses only data dated before move_start."""
    sym, start = row['symbol'], row['move_start']
    if sym not in universe_syms: return 'not in universe', None
    h = hist[(hist['symbol'] == sym) & (hist['date'] <= start)]
    if h.empty:
        return ('no history before the move (logging started later)' if hist.empty or hist['date'].min() > start
                else 'not eligible (liquidity/market cap) before the move'), None
    t = transitions[(transitions['symbol'] == sym) & (transitions['date'] <= start)] if len(transitions) else transitions
    if len(t) and t['to'].isin(['STARTER', 'BUILD', 'CORE']).any(): return 'caught: starter before the move', None
    if len(t) and (t['to'] == 'RESEARCH').any(): return 'researched but no starter before the move', None
    sg = signals[(signals['symbol'] == sym) & (signals['date'] <= start)] if len(signals) else signals
    best = h['discovery'].max() if 'discovery' in h else None
    if len(sg): return 'material signal logged but not escalated', best
    if best is not None and best >= 40: return 'discovery score elevated but below research threshold', best
    return 'no deterministic signal before the move', best


def run(frames, universe_syms, session):
    AUDIT.mkdir(parents=True, exist_ok=True)
    m = movers(frames, session)
    hist = _history()
    signals = pd.read_json(INF/'signals.jsonl', lines=True) if (INF/'signals.jsonl').exists() else pd.DataFrame(columns=['symbol', 'date'])
    trans = pd.read_json(INF/'transitions.jsonl', lines=True) if (INF/'transitions.jsonl').exists() else pd.DataFrame(columns=['symbol', 'date', 'to'])
    for df in (signals, trans):
        if len(df): df['date'] = df['date'].astype(str)
    path = AUDIT/'missed.jsonl'
    known = {(r['symbol'], r['move_start']) for r in map(json.loads, path.read_text(encoding='utf-8').splitlines())} if path.exists() else set()
    new = []
    for _, r in m.iterrows():
        if (r['symbol'], r['move_start']) in known: continue
        why, best = diagnose(r, universe_syms, hist, signals, trans)
        new.append({**r.to_dict(), 'detected_on': session, 'diagnosis': why, 'best_discovery_before': best,
                    'review': 'pending: reconstruct filings 30/60/90 days before move_start; propose rule; test on controls'})
    with path.open('a', encoding='utf-8') as f:
        for x in new: f.write(json.dumps(x, sort_keys=True, default=str)+'\n')
    precision(frames, session)
    return new


def precision(frames, session, horizons=(20, 60, 120)):
    """Forward excess return of every logged signal versus Nifty 500, by signal reason type."""
    p = INF/'signals.jsonl'
    if not p.exists(): return None
    sig = pd.read_json(p, lines=True)
    if sig.empty: return None
    bench = benchmark(); rows = []
    for _, s in sig.iterrows():
        f = frames.get(s['symbol'])
        if f is None: continue
        c = f['close']; d = pd.Timestamp(str(s['date'])[:10])
        after = c[c.index >= d]
        if not len(after): continue
        base = after.iloc[0]; b0 = bench.loc[:d]
        if not len(b0): continue
        r = {'symbol': s['symbol'], 'date': str(s['date'])[:10], 'desc': s['desc'], 'reasons': s.get('reasons', '')}
        for h in horizons:
            if len(after) > h:
                bh = bench.loc[:after.index[h]].iloc[-1]
                r[f'excess_{h}d_pct'] = round(((after.iloc[h]/base-1)-(bh/b0.iloc[-1]-1))*100, 1)
        rows.append(r)
    df = pd.DataFrame(rows)
    if df.empty: return None
    df['type'] = df['reasons'].fillna('').str.extract(r'^([a-zA-Z /-]+)')[0].str.strip().fillna(df['desc'])
    agg = df.groupby('type').agg(firings=('symbol', 'size'),
                                 **{f'mean_excess_{h}d': (f'excess_{h}d_pct', 'mean') for h in horizons if f'excess_{h}d_pct' in df},
                                 **{f'hit_rate_{h}d': (f'excess_{h}d_pct', lambda x: round(float((x > 0).mean()*100), 1) if x.notna().any() else None)
                                    for h in horizons if f'excess_{h}d_pct' in df})
    AUDIT.mkdir(parents=True, exist_ok=True)
    df.to_csv(AUDIT/'signal_outcomes.csv', index=False)
    agg.round(2).to_csv(AUDIT/'signal_precision.csv')
    return agg


STL_CASE = {
    'symbol': 'STLTECH', 'move_start': '2026-01-23', 'start_price': 88.4, 'end_price': 955.3, 'window_sessions': 170,
    'excess_return_pct': None, 'detected_on': '2026-10-03', 'case': 1,
    'diagnosis': 'not in universe (Nifty Total Market list filtered to EQ series; STL was in BE series)',
    'earliest_signals': [
        {'date': '2026-02-02', 'signal': 'NSE price-movement query', 'price': 106},
        {'date': '2026-02-07', 'signal': 'promoter warrants Rs498 cr at Rs110 (~10% of market cap)', 'price': 140},
        {'date': '2026-04-29', 'signal': 'Q4 FY26: revenue +37%, operating profit 2.6x, turnaround', 'price': 280},
        {'date': '2026-05-22', 'signal': 'hyperscaler award ~USD 1.11 bn (FY27-29) ~66% of FY26 revenue a year', 'price': 441}],
    'best_non_hindsight_detection': {'date': '2026-05-22', 'price': 441, 'state': 'STARTER'},
    'rules_added': ['universe = all NSE EQ + BE equities with >=Rs500 cr mcap and >=Rs1 cr turnover',
                    'order intensity from filing PDFs (value / tenure x firmness / TTM revenue), fast lane at >=20%',
                    'promoter preferential conviction (size vs mcap, price vs market)',
                    'exchange surveillance query joined to a material filing opens research'],
    'predictive_or_hindsight': 'Feb signals ambiguous (loss-making, indebted company raising money); May 22 award was a genuine, quantifiable signal',
    'false_positive_check': 'pending: signal_precision.csv over all firings of each rule',
    'review': 'done (docs/ARCHITECTURE_V3.md section J)'}


def seed_cases():
    AUDIT.mkdir(parents=True, exist_ok=True)
    path = AUDIT/'missed.jsonl'
    rows = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    if not any('"case": 1' in r for r in rows):
        with path.open('a', encoding='utf-8') as f: f.write(json.dumps(STL_CASE, sort_keys=True)+'\n')
