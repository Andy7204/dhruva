"""Forward performance table and the pre-registered verdict for each book."""
from datetime import date

import numpy as np
import pandas as pd

RF = 0.06  # same flat cash assumption as the research engine


def verdict(series, bench, c):
    first, last = series.index[0], series.index[-1]
    years = (date.fromisoformat(last)-date.fromisoformat(first)).days/365.25
    paper, ref = series.iloc[-1]/series.iloc[0], bench.iloc[-1]/bench.iloc[0]
    worst = float((series/series.cummax()-1).min()*100)
    shortfall = (ref-paper)*100
    if -worst > c['max_drawdown_limit_pct']:
        return 'FAIL', 'Drawdown breached the limit'
    if years >= c['early_fail_after_years'] and shortfall >= c['early_fail_cumulative_shortfall_pct']:
        return 'FAIL', 'Trails Nifty 50 by the early-fail margin'
    if years >= c['earliest_verdict_years']:
        excess = (paper**(1/years)-ref**(1/years))*100
        if excess >= c['pass_min_excess_cagr_pct']:
            return 'PASS', 'Beat Nifty 50 by the required margin'
        if years >= c['final_verdict_years']:
            return 'FAIL', 'Final verdict without the required margin'
    return 'INCONCLUSIVE', f'{years:.2f} of {c["earliest_verdict_years"]} years'


def summary(hist, criteria):
    rows = []
    bench = hist['N50'].dropna() if 'N50' in hist else None
    for book in hist.columns:
        s = hist[book].dropna()
        if len(s) < 2: continue
        years = (date.fromisoformat(s.index[-1])-date.fromisoformat(s.index[0])).days/365.25
        r = s.pct_change().dropna()
        ex = r-(1+RF)**(1/252)+1
        row = {'Book': book, 'Since': s.index[0], 'Return %': round((s.iloc[-1]/s.iloc[0]-1)*100, 2),
               'Max drawdown %': round(float((s/s.cummax()-1).min()*100), 2),
               'Annualized %': round(((s.iloc[-1]/s.iloc[0])**(1/years)-1)*100, 2) if years >= 1 else None,
               'Sharpe': round(float(ex.mean()/ex.std()*np.sqrt(252)), 2) if len(r) >= 126 and ex.std() > 0 else None,
               'Sortino': round(float(ex.mean()/np.sqrt((ex.clip(upper=0)**2).mean())*np.sqrt(252)), 2) if len(r) >= 126 else None}
        if bench is not None and book != 'N50':
            b = bench.reindex(s.index).dropna()
            row['vs Nifty 50 (points)'] = round((s.iloc[-1]/s.iloc[0]-b.iloc[-1]/b.iloc[0])*100, 2)
            row['Verdict'], row['Reason'] = verdict(s.loc[b.index], b, criteria)
        rows.append(row)
    return rows
