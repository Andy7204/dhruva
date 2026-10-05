"""Discovery-D: deterministic early-inflection score (0-100) for every stock.

Asks "what public, numeric evidence says earnings could look very different
2-4 quarters from now?" before results show it. Only filings with quantities
count; price never adds points. Weights fixed 2026-10-03 (docs/ARCHITECTURE_V3.md).
"""
import pandas as pd

from scanner.score import ramp, s

WEIGHTS = {'order_intensity': 25, 'tier1_customer': 10, 'capacity': 15, 'commissioning': 5,
           'promoter_conviction': 15, 'margin_inflection': 10, 'turnaround': 10, 'early_volume': 5,
           'rating_upgrade': 5}


def _window(events, sym, as_of, days):
    if events is None or not len(events): return events
    e = events[events['symbol'] == sym]
    d = pd.to_datetime(e['date'])
    return e[(d <= pd.Timestamp(as_of)) & (d > pd.Timestamp(as_of)-pd.Timedelta(days=days))]


def features(sym, fund, events, as_of):
    f = fund or {}
    x, pts = {}, {}
    e180 = _window(events, sym, as_of, 180)
    e365 = _window(events, sym, as_of, 365)
    orders = e180[e180['desc'] == 'Bagging/Receiving of orders/contracts'] if e180 is not None and len(e180) else pd.DataFrame()
    x['order_intensity_180d'] = float(orders['order_intensity'].fillna(0).sum()) if 'order_intensity' in orders else 0.
    x['tier1_order_180d'] = bool(orders['tier1_customer'].fillna(False).any()) if 'tier1_customer' in orders else False
    cap = e365[e365['desc'] == 'Capacity addition'] if e365 is not None and len(e365) else pd.DataFrame()
    x['capacity_pct_365d'] = float(cap['capacity_pct'].max()) if 'capacity_pct' in cap and cap['capacity_pct'].notna().any() else 0.
    com = e180[e180['desc'] == 'Commencement of commercial production/operations'] if e180 is not None and len(e180) else pd.DataFrame()
    x['commissioning_180d'] = len(com)
    pref = e365[e365['desc'] == 'Preferential issue'] if e365 is not None and len(e365) else pd.DataFrame()
    conv = 0.
    if len(pref) and 'promoter_pct_mcap' in pref:
        ok = pref[(pref['promoter'].fillna(False)) & (pref.get('price_ratio', pd.Series(dtype=float)).fillna(0) >= 0.9)]
        conv = float(ok['promoter_pct_mcap'].fillna(0).max()) if len(ok) else 0.
    x['promoter_pct_mcap_365d'] = conv
    rat = e365[e365['desc'].str.startswith('Credit Rating')] if e365 is not None and len(e365) else pd.DataFrame()
    x['rating_upgrade_365d'] = bool((rat.get('rating_move', pd.Series(dtype=float)).fillna(0) >= 1).any()) if len(rat) else False
    x['dilution_365d'] = bool(len(e365[e365['desc'] == 'Qualified Institutional Placement'])) if e365 is not None and len(e365) else False
    # margin inflection from a low base, on core EBITDA (operating income + depreciation)
    rev, op, dep = s(f, 'quarterlyTotalRevenue'), s(f, 'quarterlyOperatingIncome'), s(f, 'quarterlyReconciledDepreciation')
    pbt, other = s(f, 'quarterlyPretaxIncome'), s(f, 'quarterlyOtherNonOperatingIncomeExpenses')
    if len(rev) >= 2 and len(op) >= 2 and len(dep) >= 2 and rev[-1] > 0 and rev[-2] > 0:
        m_now, m_prev = (op[-1]+dep[-1])/rev[-1]*100, (op[-2]+dep[-2])/rev[-2]*100
        arev, aebitda = s(f, 'annualTotalRevenue'), s(f, 'annualEBITDA')
        hist = [b/a*100 for a, b in zip(arev, aebitda) if a and a > 0]
        median = sorted(hist)[len(hist)//2] if hist else None
        x['core_margin_qoq_change'] = m_now-m_prev
        x['core_margin_vs_history'] = (m_now-median) if median is not None else None
        low_base = median is None or m_prev <= median+2
        pts_margin = ramp(m_now-m_prev, 1, 6) if low_base else 0.
    else:
        pts_margin = 0.
    core = [p-o for p, o in zip(pbt[-len(other):], other)] if len(pbt) >= 5 and len(other) >= 5 else []
    x['core_turnaround'] = bool(core and core[-1] > 0 and sum(1 for c in core[-5:-1] if c <= 0) >= 2)
    x['rev_qoq'] = (rev[-1]/rev[-2]-1)*100 if len(rev) >= 2 and rev[-2] > 0 else None
    pts = {'order_intensity': ramp(x['order_intensity_180d'], 0.05, 0.5), 'tier1_customer': float(x['tier1_order_180d']),
           'capacity': ramp(x['capacity_pct_365d'], 10, 50), 'commissioning': float(x['commissioning_180d'] > 0),
           'promoter_conviction': ramp(conv, 1, 8), 'margin_inflection': pts_margin,
           'turnaround': float(x['core_turnaround']), 'early_volume': ramp(x['rev_qoq'], 5, 25),
           'rating_upgrade': float(x['rating_upgrade_365d'])}
    score = sum(WEIGHTS[k]*pts[k] for k in WEIGHTS)
    return round(score, 1), x, {k: round(WEIGHTS[k]*v, 1) for k, v in pts.items()}


def score_all(symbols, fund, events, as_of):
    rows = []
    for sym in symbols:
        sc, x, pts = features(sym, fund.get(sym), events, as_of)
        rows.append({'symbol': sym, 'discovery_score': sc, **{f'disc_{k}': v for k, v in pts.items()},
                     **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()}})
    return pd.DataFrame(rows)
