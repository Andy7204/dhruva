"""Stage 1: quantitative inflection score for every stock (0-100).

Implements the measurable part of docs/MULTIBAGGER.md: revenue acceleration,
operating leverage, PAT/EPS acceleration, earnings quality, cash-flow forensics,
balance sheet, valuation gap and filing catalysts. Governance red flags veto.
Price trend is recorded for entry timing only; it does not add to the score,
because the aim is to find fundamentals changing before prices fully react.

Inputs are only what was public at the scan date's close. Missing data scores
zero for that part and is listed; it is never assumed good.
"""
import math

import numpy as np
import pandas as pd

WEIGHTS = {'revenue': 15, 'leverage': 15, 'profit': 15, 'quality': 10, 'cash': 15,
           'balance': 10, 'valuation': 15, 'catalysts': 5}
POSITIVE = {'Bagging/Receiving of orders/contracts': 1.0, 'Commencement of commercial production/operations': 1.5,
            'Credit Rating- New': 0.3, 'Credit Rating- Revision': 0.2, 'Acquisition': 0.2}
RED_FLAGS = ('Corporate Insolvency Resolution Process', 'Resignation of Auditor', 'Default', 'Fraud')  # veto: serious governance or solvency events
WATCH_FLAGS = ('Change in Auditors', 'Pendency of Litigation(s)/dispute(s) or the outcome impacting the Company',
               'Action(s) taken or orders passed', 'Action(s) initiated or orders passed')  # routine tax/legal notices: Stage 3 judges


def ramp(x, zero, full):
    """0 at `zero`, 1 at `full`, linear between; None/NaN scores 0."""
    if x is None or x != x or not math.isfinite(x): return 0.
    return float(min(1., max(0., (x-zero)/(full-zero))))


def s(f, key):
    return [v for _, v in (f or {}).get(key, [])]


def growth(now, then):
    return (now/then-1)*100 if then and then > 0 and now is not None else None


def technicals(frame):
    c, v = frame['close'], frame['volume'].fillna(0)
    if len(c) < 130: return None
    ma50, ma150, ma200 = c.rolling(50).mean(), c.rolling(150).mean(), c.rolling(200, min_periods=130).mean()
    hi, lo = c.rolling(252, min_periods=130).max(), c.rolling(252, min_periods=130).min()
    last = c.iloc[-1]
    ret = lambda n: c.iloc[-1]/c.iloc[-min(n, len(c)-1)-1]-1
    template = [last > ma150.iloc[-1], last > ma200.iloc[-1], ma150.iloc[-1] > ma200.iloc[-1],
                ma200.iloc[-1] > ma200.iloc[-21], ma50.iloc[-1] > ma150.iloc[-1], last > ma50.iloc[-1],
                last >= 1.3*lo.iloc[-1], last >= 0.75*hi.iloc[-1]]
    vol50 = v.rolling(50).mean().iloc[-1]
    return {'close': float(last), 'ma50': float(ma50.iloc[-1]), 'rs_raw': float(2*ret(63)+ret(126)+ret(189)+ret(252)),
            'stage2': all(bool(t) for t in template), 'ret_12m_pct': float(ret(252)*100),
            'from_high_pct': float((last/hi.iloc[-1]-1)*100),
            'breakout': bool(vol50 > 0 and last > c.iloc[-51:-1].max() and v.iloc[-1] >= 1.5*vol50),
            'turnover_cr': float((c*v).iloc[-20:].mean()/1e7)}


def fundamentals(f, close, ret_12m):
    """All ratios the framework asks for that free data supports. Returns (parts, facts, flags)."""
    rev, ebitda, nebitda = s(f, 'quarterlyTotalRevenue'), s(f, 'quarterlyEBITDA'), s(f, 'quarterlyNormalizedEBITDA')
    pat, eps, pbt, tax = s(f, 'quarterlyNetIncome'), s(f, 'quarterlyDilutedEPS'), s(f, 'quarterlyPretaxIncome'), s(f, 'quarterlyTaxProvision')
    unusual, interest = s(f, 'quarterlyTotalUnusualItems'), s(f, 'quarterlyInterestExpense')
    x, flags = {}, []
    ok = len(rev) >= 5 and len(pat) >= 5
    x['quarters'] = len(rev)
    if ok:
        x['rev_yoy'] = growth(rev[-1], rev[-5]); x['rev_qoq'] = growth(rev[-1], rev[-2])
        x['rev_qoq_prev'] = growth(rev[-2], rev[-3])
        x['rev_up_quarters'] = sum(1 for a, b in zip(rev[-4:], rev[-5:-1]) if a > b)
        x['pat_yoy'] = growth(pat[-1], pat[-5])
        x['turnaround'] = pat[-1] > 0 and min(pat[-5:-1]) <= 0
        x['pat_margin'] = pat[-1]/rev[-1]*100 if rev[-1] > 0 else None
    if ok and len(ebitda) >= 5:
        x['ebitda_yoy'] = growth(ebitda[-1], ebitda[-5])
        x['ebitda_margin'] = ebitda[-1]/rev[-1]*100 if rev[-1] > 0 else None
        x['ebitda_margin_change'] = (ebitda[-1]/rev[-1]-ebitda[-5]/rev[-5])*100 if rev[-1] > 0 and rev[-5] > 0 else None
        d_rev = rev[-1]-rev[-5]
        x['incremental_ebitda_margin'] = (ebitda[-1]-ebitda[-5])/d_rev*100 if d_rev > 0 else None
        if (x.get('rev_yoy') or 0) > 60 and (x.get('ebitda_yoy') or 0) < (x['rev_yoy'])/2:
            flags.append('low-quality growth: EBITDA lags revenue')
    if len(eps) >= 5:
        x['eps_yoy'] = growth(eps[-1], eps[-5])
        ttm = sum(eps[-4:]); x['pe'] = close/ttm if ttm > 0 else None
    if nebitda and ebitda and ebitda[-1]:
        x['one_off_share'] = abs(ebitda[-1]-nebitda[-1])/abs(ebitda[-1])*100
    if unusual and pbt and pbt[-1]:
        x['unusual_share_of_pbt'] = abs(unusual[-1])/abs(pbt[-1])*100
    if tax and pbt and pbt[-1] > 0:
        x['tax_rate'] = tax[-1]/pbt[-1]*100
    # annual cash-flow forensics
    cfo, capex, fcf = s(f, 'annualOperatingCashFlow'), s(f, 'annualCapitalExpenditure'), s(f, 'annualFreeCashFlow')
    apat, arev, rec, inv = s(f, 'annualNetIncome'), s(f, 'annualTotalRevenue'), s(f, 'annualAccountsReceivable'), s(f, 'annualInventory')
    if cfo and apat and apat[-1] > 0:
        x['cfo_to_pat'] = cfo[-1]/apat[-1]
        if len(cfo) >= 2 and len(apat) >= 2 and apat[-1] > apat[-2] and cfo[-1] < cfo[-2]:
            flags.append('PAT up while CFO down')
    if fcf: x['fcf_positive'] = fcf[-1] > 0
    if len(arev) >= 2 and arev[-2] > 0:
        x['annual_rev_growth'] = growth(arev[-1], arev[-2])
        if len(rec) >= 2 and rec[-2] > 0:
            x['receivables_growth'] = growth(rec[-1], rec[-2])
            if x['receivables_growth'] > x['annual_rev_growth']+25: flags.append('receivables growing much faster than revenue')
        if len(inv) >= 2 and inv[-2] > 0:
            x['inventory_growth'] = growth(inv[-1], inv[-2])
            if x['inventory_growth'] > x['annual_rev_growth']+25: flags.append('inventory growing much faster than revenue')
    if rec and arev and arev[-1] > 0: x['receivable_days'] = rec[-1]/arev[-1]*365
    x['cash_flow_class'] = ('A productive growth investment' if cfo and fcf and cfo[-1] > 0 and fcf[-1] < 0 else
                            'C/D weak: negative operating cash flow' if cfo and cfo[-1] < 0 else
                            'healthy' if fcf and fcf[-1] > 0 else 'unknown')
    # balance sheet
    netdebt, aebitda, shares, equity, ic = (s(f, k) for k in ('annualNetDebt', 'annualEBITDA', 'annualOrdinarySharesNumber',
                                                             'annualStockholdersEquity', 'annualInvestedCapital'))
    debt, cash = s(f, 'annualTotalDebt'), s(f, 'annualCashAndCashEquivalents')
    nd = netdebt[-1] if netdebt else (debt[-1]-(cash[-1] if cash else 0) if debt else None)
    if nd is not None and aebitda and aebitda[-1] > 0: x['net_debt_to_ebitda'] = nd/aebitda[-1]
    if interest and ebitda and interest[-1] > 0: x['interest_cover'] = ebitda[-1]/interest[-1]
    if len(shares) >= 2 and shares[-2] > 0:
        x['dilution_pct'] = growth(shares[-1], shares[-2])
        if x['dilution_pct'] > 10: flags.append('equity dilution over 10% in a year')
    if ic and aebitda and ic[-1] > 0: x['roce_proxy'] = aebitda[-1]/ic[-1]*100  # EBITDA/invested capital
    if equity and apat and equity[-1] > 0: x['roe'] = apat[-1]/equity[-1]*100
    qshares = s(f, 'quarterlyOrdinarySharesNumber') or shares
    if qshares:
        x['market_cap_cr'] = close*qshares[-1]/1e7
        if nd is not None and aebitda and aebitda[-1] > 0:
            x['ev_to_ebitda'] = (close*qshares[-1]+nd)/aebitda[-1]
    if x.get('pe') and (x.get('eps_yoy') or 0) > 0: x['peg'] = x['pe']/x['eps_yoy']
    if x.get('eps_yoy') is not None and ret_12m is not None:
        x['expectation_gap'] = min(x['eps_yoy'], 200)-ret_12m  # EPS growth not yet reflected in price
    parts = {
        'revenue': 0.5*ramp(x.get('rev_yoy'), 5, 40)+0.25*ramp(x.get('rev_up_quarters'), 1, 4)
                   + 0.25*float((x.get('rev_qoq') or -1) > (x.get('rev_qoq_prev') or 0) and (x.get('rev_qoq') or 0) > 0),
        'leverage': (0.4*ramp((x.get('ebitda_yoy') or 0)/max(x.get('rev_yoy') or 0, 5), 0.8, 1.8)
                     + 0.3*ramp((x.get('incremental_ebitda_margin') or 0)-(x.get('ebitda_margin') or 0), 0, 15)
                     + 0.3*ramp(x.get('ebitda_margin_change'), 0, 5)) if ok else 0.,
        'profit': (1. if x.get('turnaround') else 0.6*ramp(x.get('pat_yoy'), 10, 70)
                   + 0.4*float((x.get('pat_yoy') or 0) > (x.get('ebitda_yoy') or 0) > (x.get('rev_yoy') or 0) > 0)),
        'quality': 0.5*(1-ramp(x.get('unusual_share_of_pbt'), 10, 40) if 'unusual_share_of_pbt' in x else .3)
                   + 0.5*(1.-ramp(abs((x.get('tax_rate') or 25)-25), 10, 25)),
        'cash': 0.5*ramp(x.get('cfo_to_pat'), 0.3, 0.9)
                + 0.25*(0 if 'receivables growing much faster than revenue' in flags else 1 if 'receivables_growth' in x else .3)
                + 0.25*(1 if x['cash_flow_class'] in ('healthy', 'A productive growth investment') else 0),
        'balance': 0.4*(1-ramp(x.get('net_debt_to_ebitda'), 1, 3.5) if 'net_debt_to_ebitda' in x else .5)
                   + 0.3*ramp(x.get('interest_cover'), 2, 8) + 0.3*(1-ramp(x.get('dilution_pct'), 3, 15)),
        'valuation': 0.4*(ramp(-x['peg'], -2.5, -0.7) if x.get('peg') else .2) + 0.4*ramp(x.get('expectation_gap'), 0, 60)
                     + 0.2*ramp(-(x.get('market_cap_cr') or 1e6), -60000, -3000),
    }
    return parts, x, flags, ok


def catalysts(items):
    pos = [a for a in items if a['desc'] in POSITIVE]
    red = sorted({a['desc'] for a in items if _red((a['desc'] or '').lower())})
    watch = sorted({a['desc'] for a in items if a['desc'] in WATCH_FLAGS})
    return min(1., sum(POSITIVE[a['desc']] for a in pos)/2), {'legal_or_regulatory_90d': '; '.join(watch),
        'orders_90d': sum(a['desc'] == 'Bagging/Receiving of orders/contracts' for a in pos),
        'capacity_90d': sum(a['desc'] == 'Commencement of commercial production/operations' for a in pos),
        'red_flags': red}


def scan(uni, frames, fund, news, news_ok=True, cutoff_days=90, as_of=None):
    tech = {k: t for k, t in ((k, technicals(frames[k])) for k in uni['symbol'] if k in frames) if t}
    rs = pd.Series({k: t['rs_raw'] for k, t in tech.items()}).rank(pct=True)*100
    meta = uni.set_index('symbol')
    recent = {}
    limit = (pd.Timestamp(as_of)-pd.Timedelta(days=cutoff_days)) if as_of else None
    for a in news:
        if limit is not None and a.get('time') and pd.Timestamp(str(a['time'])[:10]) < limit: continue
        recent.setdefault(a['symbol'], []).append(a)
    rows = []
    for k, t in tech.items():
        parts, x, flags, ok = fundamentals(fund.get(k), t['close'], t['ret_12m_pct'])
        c, cinfo = catalysts(recent.get(k, [])) if news_ok else (0.3, {'legal_or_regulatory_90d': '', 'orders_90d': None, 'capacity_90d': None, 'red_flags': []})
        parts['catalysts'] = c
        score = sum(WEIGHTS[p]*parts[p] for p in WEIGHTS) if ok else 0.
        veto = cinfo['red_flags']
        rows.append({'symbol': k, 'name': meta['name'].get(k), 'industry': meta['industry'].get(k),
                     'stage1_score': round(score, 1), 'fundamentals_ok': ok, 'veto': '; '.join(veto),
                     'flags': '; '.join(flags), **{f'{p}_pts': round(WEIGHTS[p]*parts[p], 1) for p in WEIGHTS},
                     **{key: _r(val) for key, val in x.items()}, **cinfo, 'red_flags': '; '.join(cinfo['red_flags']),
                     'close': round(t['close'], 2), 'ma50': round(t['ma50'], 2), 'rs_rank': round(float(rs[k]), 1),
                     'stage2_trend': t['stage2'], 'breakout': t['breakout'], 'ret_12m_pct': round(t['ret_12m_pct'], 1),
                     'from_high_pct': round(t['from_high_pct'], 1), 'turnover_cr': round(t['turnover_cr'], 2)})
    return pd.DataFrame(rows).sort_values('stage1_score', ascending=False).reset_index(drop=True)


def _r(v):
    if isinstance(v, bool) or isinstance(v, str) or v is None: return v
    return round(float(v), 2) if math.isfinite(v) else None


def _red(desc):
    """Veto-level filings: insolvency, default, fraud, or an auditor resigning."""
    return ('insolvency' in desc or 'default' in desc or 'fraud' in desc
            or ('auditor' in desc and 'resign' in desc))
