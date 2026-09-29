"""Index-level strategy backtester with ETF costs and Indian tax.

Design choices, all deliberately conservative:
- Signals use closes up to day t; trades fill at the close of day t+1 (one-day lag).
- Assets are Total Return Indices (dividends reinvested), each traded through an
  ETF: annual expense drag plus a per-side trading cost (spread, impact, STT,
  exchange, GST, stamp).
- Tax: FIFO lots. Equity ETFs: STCG 20% (<=365 days), LTCG 12.5% above the
  exemption. Gold/international ETFs: LTCG 12.5% after 730 days, else slab.
  Liquid (1D rate) gains always at slab. Losses offset gains within a financial
  year and carry forward 8 years, simplified. Tax is paid from cash each April.
- Every metric uses liquidation value: NAV minus the tax that selling everything
  would trigger, so buy-and-hold is never flattered by deferred tax.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent/'data'

# asset: (file, kind, annual expense drag, per-side trading cost)
ASSETS = {
    'N50':    ('NIFTY_50', 'equity', .0005, .0010),
    'NN50':   ('NIFTY_NEXT_50', 'equity', .0015, .0015),
    'N500':   ('NIFTY_500', 'equity', .0015, .0015),
    'MID150': ('NIFTY_MIDCAP_150', 'equity', .0020, .0020),
    'SML250': ('NIFTY_SMALLCAP_250', 'equity', .0030, .0030),
    'MOM30':  ('NIFTY200_MOMENTUM_30', 'equity', .0030, .0020),
    'MIDMOM50': ('NIFTY_MIDCAP150_MOMENTUM_50', 'equity', .0030, .0030),
    'MOM50':  ('NIFTY500_MOMENTUM_50', 'equity', .0030, .0025),
    'ALPHA50': ('NIFTY_ALPHA_50', 'equity', .0030, .0030),
    'LOWVOL30': ('NIFTY100_LOW_VOLATILITY_30', 'equity', .0030, .0020),
    'QUAL30': ('NIFTY200_QUALITY_30', 'equity', .0030, .0020),
    'VAL30':  ('NIFTY200_VALUE_30', 'equity', .0030, .0025),
    'ALPLV30': ('NIFTY_ALPHA_LOW_VOLATILITY_30', 'equity', .0030, .0025),
    'MIDQUAL50': ('NIFTY_MIDCAP150_QUALITY_50', 'equity', .0030, .0030),
    'NDX':    ('NASDAQ100_INR', 'foreign', .0060, .0030),
    'GOLD':   ('GOLD_SPLICED', 'gold', .0080, .0020),
    'LIQ':    ('NIFTY_1D_RATE_INDEX', 'liquid', .0070, .0005),
}
SLAB = 0.312  # 30% slab plus 4% cess, as in config.json's income scenario


def load(names=None):
    names = names or list(ASSETS)
    series = {}
    for a in names:
        f = DATA/(ASSETS[a][0]+'.csv')
        if a == 'GOLD':
            series[a] = _gold()
            continue
        if a == 'LIQ':
            continue  # built on the trading calendar below
        if f.exists():
            s = pd.read_csv(f, index_col='date', parse_dates=True)['tri']
            series[a] = s[~s.index.duplicated()].sort_index()
    cal = series['N50'].index
    if 'LIQ' in names:
        # ASSUMPTION: no free official overnight-rate history; flat 6% a year before
        # the fund's expense drag, accrued per calendar day.
        days = (cal-cal[0]).days.to_numpy()
        series['LIQ'] = pd.Series(100*1.06**(days/365), index=cal)
    frame = pd.DataFrame({a: s.reindex(cal.union(s.index)).ffill(limit=5).reindex(cal) for a, s in series.items()})
    return frame


def _gold():
    """INR gold: international gold x USDINR until GOLDBEES exists, then GOLDBEES."""
    world = pd.read_csv(DATA/'GOLD_INR.csv', index_col='date', parse_dates=True)['tri']
    bees = pd.read_csv(DATA/'GOLDBEES.csv', index_col='date', parse_dates=True)['tri']
    a = bees.to_numpy(); keep = np.ones(len(a), bool); i = 1
    while i < len(a):  # drop >50% moves that revert within 5 sessions (Dec 2019 split glitch)
        if abs(a[i]/a[i-1]-1) > .5:
            back = next((j for j in range(i+1, min(i+6, len(a))) if abs(a[j]/a[i-1]-1) < .25), None)
            if back: keep[i:back] = False; i = back; continue
        i += 1
    bees = bees[keep]
    start = bees.index[0]
    head = world[world.index < start]
    return pd.concat([head*bees.iloc[0]/world[world.index <= start].iloc[-1], bees])


@dataclass
class Lot:
    qty: float
    cost: float
    day: pd.Timestamp


@dataclass
class Account:
    cash: float
    lots: dict = field(default_factory=dict)
    realized: dict = field(default_factory=dict)  # fy -> {'st','lt','slab'}
    carry_st: float = 0.
    carry_lt: float = 0.
    tax_paid: float = 0.
    costs: float = 0.
    trades: int = 0


def fy(day):
    return day.year if day.month >= 4 else day.year-1


def classify(asset, held_days, gain):
    kind = ASSETS[asset][1]
    if kind == 'liquid' or kind == 'debt':
        return 'slab'
    if kind == 'equity':
        return 'lt' if held_days > 365 else 'st'
    return 'lt' if held_days > 730 else 'slab'  # gold / foreign


def settle_tax(acct, year, final=False):
    """Net one financial year's gains, apply carry-forward, return tax due."""
    g = acct.realized.pop(year, {'st': 0., 'lt': 0., 'slab': 0.})
    st, lt, slab = g['st'], g['lt'], g['slab']
    # Short-term (incl. slab) losses can offset anything; long-term only long-term.
    stl = min(0, st)+min(0, slab)-acct.carry_st
    st, slab = max(0, st), max(0, slab)
    lt -= acct.carry_lt
    acct.carry_st = acct.carry_lt = 0.
    for bucket in ('slab', 'st', 'lt'):
        if stl >= 0: break
        cur = {'slab': slab, 'st': st, 'lt': lt}[bucket]
        use = min(max(cur, 0), -stl); stl += use
        if bucket == 'slab': slab -= use
        elif bucket == 'st': st -= use
        else: lt -= use
    if lt < 0: acct.carry_lt = -lt; lt = 0
    if stl < 0: acct.carry_st = -stl
    lt = max(0, lt-125000*EXEMPTION_SCALE)
    tax = (st*.20+lt*.125)*1.04+slab*SLAB
    return tax


EXEMPTION_SCALE = 0.0  # 0 = ignore the INR1.25 lakh exemption (conservative, capital-size neutral)


def liquidation_tax(acct, prices, day):
    """Tax that selling everything today would add, including this year's realized gains."""
    import copy
    a = copy.deepcopy(acct)
    for asset, lots in a.lots.items():
        for lot in lots:
            gain = lot.qty*(prices[asset]-lot.cost)
            b = classify(asset, (day-lot.day).days, gain)
            a.realized.setdefault(fy(day), {'st': 0., 'lt': 0., 'slab': 0.})[b] += gain
    return sum(settle_tax(a, y) for y in sorted(a.realized))


def run(prices: pd.DataFrame, strategy, start, end, rebalance_band=0.0, capital=1_000_000.):
    """strategy(i, prices) -> target weights (sum <= 1; remainder in LIQ)."""
    cal = prices.index
    acct = Account(cash=capital)
    drag = {a: (1-ASSETS[a][2])**(1/252) for a in prices}
    nav, liq, weights_log = [], [], []
    pending = None
    last_fy = fy(cal[start])
    for i in range(start, end+1):
        day = cal[i]; px = prices.iloc[i]
        # expense drag: shrink units slightly each session
        for a, lots in acct.lots.items():
            for lot in lots: lot.qty *= drag[a]
        if fy(day) != last_fy:
            due = settle_tax(acct, last_fy)
            acct.cash -= due; acct.tax_paid += due
            last_fy = fy(day)
        if pending is not None:
            _trade(acct, pending, px, day, rebalance_band)
            pending = None
        value = acct.cash+sum(l.qty*px[a] for a, ls in acct.lots.items() for l in ls)
        nav.append(value)
        liq.append(value-liquidation_tax(acct, px, day) if i % 5 == 0 or i == end else np.nan)
        if i < end:
            target = strategy(i, prices)
            if target is not None:
                pending = target
                weights_log.append((day, target))
    out = pd.DataFrame({'nav': nav, 'liq': liq}, index=cal[start:end+1])
    out['liq'] = out['liq'].interpolate().bfill()
    return out, acct, weights_log


def _trade(acct, target, px, day, band):
    value = acct.cash+sum(l.qty*px[a] for a, ls in acct.lots.items() for l in ls)
    target = {a: w for a, w in target.items() if w > 1e-9}
    rest = max(0., 1-sum(target.values()))
    if rest > 1e-9 and 'LIQ' in px.index and not math.isnan(px['LIQ']):
        target['LIQ'] = target.get('LIQ', 0)+rest
    held = {a: sum(l.qty for l in ls)*px[a] for a, ls in acct.lots.items()}
    # sells first
    for a in list(acct.lots):
        want = target.get(a, 0)*value
        if held[a]-want > max(band*value, 1):
            _sell(acct, a, (held[a]-want)/px[a], px[a], day)
    for a, w in target.items():
        have = sum(l.qty for l in acct.lots.get(a, []))*px[a]
        want = w*value
        if want-have > max(band*value, 1) and not math.isnan(px[a]):
            spend = min(want-have, acct.cash/(1+ASSETS[a][3]))
            if spend > 1:
                cost = spend*ASSETS[a][3]
                acct.cash -= spend+cost; acct.costs += cost; acct.trades += 1
                acct.lots.setdefault(a, []).append(Lot(spend/px[a], px[a], day))


def _sell(acct, a, qty, price, day):
    proceeds = qty*price; cost = proceeds*ASSETS[a][3]
    acct.cash += proceeds-cost; acct.costs += cost; acct.trades += 1
    left = qty
    while left > 1e-12 and acct.lots.get(a):
        lot = acct.lots[a][0]; take = min(lot.qty, left)
        gain = take*(price*(1-ASSETS[a][3])-lot.cost)
        b = classify(a, (day-lot.day).days, gain)
        acct.realized.setdefault(fy(day), {'st': 0., 'lt': 0., 'slab': 0.})[b] += gain
        lot.qty -= take; left -= take
        if lot.qty <= 1e-12: acct.lots[a].pop(0)
    if not acct.lots.get(a): acct.lots.pop(a, None)


# Official launch dates. Earlier values are NSE back-calculations of rules
# designed with hindsight; only data after launch is a genuinely live record.
# Sources: niftyindices.com factsheets and press releases (QUAL30 per an April
# 18, 2018 Business Standard report of the launch).
LAUNCH = {'MOM30': '2020-08-25', 'MIDMOM50': '2022-08-16', 'ALPHA50': '2012-11-19',
          'LOWVOL30': '2016-07-08', 'QUAL30': '2018-04-18', 'ALPLV30': '2017-07-10',
          'VAL30': '2024-06-12'}


def metrics(series: pd.Series, rf: pd.Series | None = None):
    # Weekly samples: liquidation value is computed every fifth session and
    # interpolated between, which would understate daily volatility.
    s = series.dropna().resample('W-FRI').last().dropna()
    years = (s.index[-1]-s.index[0]).days/365.25
    r = s.pct_change().dropna()
    rfd = (rf.resample('W-FRI').last().reindex(s.index).ffill().pct_change().reindex(r.index).fillna(0) if rf is not None else 0*r)
    ex = r-rfd
    down = ex[ex < 0]
    dd = s/s.cummax()-1
    cagr = (s.iloc[-1]/s.iloc[0])**(1/years)-1
    return {'cagr_pct': round(cagr*100, 2), 'vol_pct': round(r.std()*np.sqrt(52)*100, 2),
            'sharpe': round(ex.mean()/ex.std()*np.sqrt(52), 3) if ex.std() > 0 else None,
            'sortino': round(ex.mean()/np.sqrt((ex.clip(upper=0)**2).mean())*np.sqrt(52), 3) if len(down) else None,
            'max_dd_pct': round(dd.min()*100, 2),
            'calmar': round(cagr/abs(dd.min()), 3) if dd.min() < 0 else None,
            'ulcer': round(float(np.sqrt((dd**2).mean())*100), 2), 'years': round(years, 2)}
