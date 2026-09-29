"""Pre-registered candidate strategies (fixed September29, 2026, before any results).

Only change after registration: the G-sec safe asset was dropped because its
history is not available from the same source; cash is used instead. Nifty50
Value 20 (history from 2009) was replaced by Nifty200 Value 30 (from 2005).

Parameters are the standard literature choices (12-month momentum, 200-day /
10-month trend, monthly or quarterly review). None is tuned on this data.
Each returns target weights at the close of day i using prices up to day i.
"""
import numpy as np

MONTH = 21


def _ret(p, a, i, n):
    if i-n < 0: return np.nan
    x, y = p[a].iloc[i-n], p[a].iloc[i]
    return y/x-1 if x == x and y == y and x > 0 else np.nan


def _review(i, start, every):
    return (i-start) % every == 0


def hold(asset):
    def s(i, p, start=None):
        return {asset: 1.0} if i == s.start else None
    s.start = None
    return s


def static(weights, every=252):
    def s(i, p):
        return dict(weights) if _review(i, s.start, every) else None
    s.start = None
    return s


def rotation(universe, top=1, lookback=252, every=MONTH, absolute=True, safe=('LIQ',), skip=0):
    """Relative strength: hold the top-N by trailing return. With `absolute`, an
    asset must also beat cash (1D rate) over the same period (dual momentum)."""
    def s(i, p):
        if not _review(i, s.start, every): return None
        scores = {a: _ret(p, a, i-skip, lookback-skip) for a in universe}
        scores = {a: v for a, v in scores.items() if v == v}
        cash = _ret(p, 'LIQ', i, lookback)
        ranked = sorted(scores, key=scores.get, reverse=True)[:top]
        w = {}
        for a in ranked:
            if absolute and not (scores[a] > (cash if cash == cash else 0)):
                pick = max(safe, key=lambda x: _ret(p, x, i, lookback) if _ret(p, x, i, lookback) == _ret(p, x, i, lookback) else -9)
                w[pick] = w.get(pick, 0)+1/top
            else:
                w[a] = w.get(a, 0)+1/top
        return w
    s.start = None
    return s


def accelerating(universe, every=MONTH, safe='LIQ'):
    """Average of 1-, 3- and 6-month returns; top-1 if positive, else safe asset."""
    def s(i, p):
        if not _review(i, s.start, every): return None
        sc = {a: np.nanmean([_ret(p, a, i, n*MONTH) for n in (1, 3, 6)]) for a in universe}
        sc = {a: v for a, v in sc.items() if v == v}
        best = max(sc, key=sc.get)
        return {best: 1.0} if sc[best] > 0 else {safe: 1.0}
    s.start = None
    return s


def trend(asset, sma=200, every=MONTH, safe='LIQ'):
    """Hold the asset while its close is above its moving average, else safe."""
    def s(i, p):
        if not _review(i, s.start, every): return None
        window = p[asset].iloc[max(0, i-sma+1):i+1]
        if len(window) < sma: return {safe: 1.0}
        return {asset: 1.0} if p[asset].iloc[i] > window.mean() else {safe: 1.0}
    s.start = None
    return s


def vol_target(asset, target=.15, window=60, every=MONTH, safe='LIQ'):
    def s(i, p):
        if not _review(i, s.start, every): return None
        r = p[asset].iloc[max(0, i-window):i+1].pct_change().dropna()
        vol = r.std()*np.sqrt(252) if len(r) > 20 else target
        w = min(1., target/vol) if vol > 0 else 1.
        return {asset: w, safe: 1-w}
    s.start = None
    return s


FACTORS = ['N50', 'NN50', 'MID150', 'SML250', 'MOM30', 'LOWVOL30', 'QUAL30', 'VAL30', 'ALPHA50']

CANDIDATES = {
    'Nifty 50 buy and hold (benchmark)': lambda: hold('N50'),
    'Nifty 500 buy and hold': lambda: hold('N500'),
    'Midcap 150 buy and hold': lambda: hold('MID150'),
    'Smallcap 250 buy and hold': lambda: hold('SML250'),
    'Nifty200 Momentum 30 buy and hold': lambda: hold('MOM30'),
    'Midcap150 Momentum 50 buy and hold': lambda: hold('MIDMOM50'),
    'Alpha 50 buy and hold': lambda: hold('ALPHA50'),
    'Low Volatility 30 buy and hold': lambda: hold('LOWVOL30'),
    'Quality 30 buy and hold': lambda: hold('QUAL30'),
    'Nifty200 Value 30 buy and hold': lambda: hold('VAL30'),
    'Alpha Low-Vol 30 buy and hold': lambda: hold('ALPLV30'),
    'Multi-factor equal weight (Mom, LowVol, Quality, Value), yearly': lambda: static({'MOM30': .25, 'LOWVOL30': .25, 'QUAL30': .25, 'VAL30': .25}),
    'Momentum 30 + Low Vol 30, 50/50 yearly': lambda: static({'MOM30': .5, 'LOWVOL30': .5}),
    'Momentum 30 60% + Gold 20% + Nasdaq-100 20%, yearly': lambda: static({'MOM30': .6, 'GOLD': .2, 'NDX': .2}),
    'Midcap Momentum 50 70% + Gold 30%, yearly': lambda: static({'MIDMOM50': .7, 'GOLD': .3}),
    'Factor rotation top-1, 12-month, monthly, dual momentum': lambda: rotation(FACTORS, 1, 252, MONTH, True, ('LIQ', 'GOLD')),
    'Factor rotation top-2, 12-month, monthly, dual momentum': lambda: rotation(FACTORS, 2, 252, MONTH, True, ('LIQ', 'GOLD')),
    'Factor rotation top-2, 6-month, quarterly, dual momentum': lambda: rotation(FACTORS, 2, 126, 63, True, ('LIQ', 'GOLD')),
    'Global dual momentum (Nifty 50, Nasdaq-100, gold), 12-month': lambda: rotation(['N50', 'NDX', 'GOLD'], 1, 252, MONTH, True, ('LIQ',)),
    'Accelerating dual momentum (Mom30, Midcap Mom50, Nasdaq-100, gold)': lambda: accelerating(['MOM30', 'MIDMOM50', 'NDX', 'GOLD']),
    'Momentum 30 with 200-day trend filter, monthly': lambda: trend('MOM30'),
    'Nifty 50 with 200-day trend filter, monthly': lambda: trend('N50'),
    'Midcap Momentum 50 with 200-day trend filter, monthly': lambda: trend('MIDMOM50'),
    'Momentum 30 volatility-targeted 15%, monthly': lambda: vol_target('MOM30'),
}
