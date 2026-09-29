"""Stage 2: narrow Stage 1 to ~10 candidates and write an evidence dossier for each.

Adds what a single company's numbers cannot show:
- industry inflection: how many peers in the same NSE industry show revenue
  growth and margin expansion at once (a proxy for demand shock / pricing power);
- score momentum: Stage 1 score now versus 20 and 60 sessions ago (68 -> 73 -> 78
  matters more than a flat 83);
- filings: order, capacity-commissioning and rating announcements in 120 days.
Supply constraints, capacity utilization and guidance need reading documents;
that is Stage 3's job.
"""
import json
from pathlib import Path

import pandas as pd

from scanner.score import ramp

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'runs'/'inflection'
RELEVANT = ('Bagging/Receiving of orders/contracts', 'Commencement of commercial production/operations',
            'Credit Rating', 'Acquisition', 'Outcome of Board Meeting', 'Investor Presentation',
            'Analysts/Institutional Investor Meet/Con. Call Updates', 'Press Release', 'Financial Result')


def industry_inflection(stage1):
    ok = stage1[stage1['fundamentals_ok']]
    grp = ok.groupby('industry')
    out = pd.DataFrame({'peers': grp.size(),
                        'share_rev_growing_20': grp.apply(lambda g: float(((g['rev_yoy'].fillna(-99)) > 20).mean())),
                        'share_margin_up': grp.apply(lambda g: float(((g['ebitda_margin_change'].fillna(-99)) > 1).mean())),
                        'median_rev_yoy': grp['rev_yoy'].median()})
    out['industry_score'] = 0.5*out['share_rev_growing_20'].apply(lambda x: ramp(x, 0.15, 0.5)) + \
        0.5*out['share_margin_up'].apply(lambda x: ramp(x, 0.3, 0.7))
    return out


def score_history(stage1, session):
    path = OUT/'score_history.csv'
    OUT.mkdir(parents=True, exist_ok=True)
    hist = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=['date', 'symbol', 'score'])
    hist = hist[hist['date'] != session]
    today = pd.DataFrame({'date': session, 'symbol': stage1['symbol'], 'score': stage1['stage1_score']})
    hist = pd.concat([hist, today])
    hist.to_csv(path, index=False)
    dates = sorted(hist['date'].unique())
    ago = lambda n: hist[hist['date'] == dates[max(0, len(dates)-1-n)]].set_index('symbol')['score']
    return ago(20), ago(60), len(dates)


def funnel(stage1, news, session, top1=50, top2=10, min_turnover_cr=1.0):
    ind = industry_inflection(stage1)
    s20, s60, days = score_history(stage1, session)
    pool = stage1[stage1['fundamentals_ok'] & (stage1['veto'].fillna('') == '') &
                  (stage1['turnover_cr'] >= min_turnover_cr)].head(top1).copy()
    pool['industry_score'] = pool['industry'].map(ind['industry_score']).fillna(0)
    pool['score_20s_ago'] = pool['symbol'].map(s20); pool['score_60s_ago'] = pool['symbol'].map(s60)
    pool['score_change_20s'] = (pool['stage1_score']-pool['score_20s_ago']) if days > 20 else None
    momentum = pool['score_change_20s'].fillna(0).apply(lambda d: ramp(d, 0, 10))
    capacity = pool['capacity_90d'].fillna(0).clip(upper=1)
    pool['stage2_score'] = (0.75*pool['stage1_score']+15*pool['industry_score']+7*momentum+3*capacity).round(1)
    pool = pool.sort_values('stage2_score', ascending=False)
    # Diversity: at most 3 finalists per industry, so one hot sector cannot crowd out the rest.
    finalists = pool[pool.groupby('industry').cumcount() < 3].head(top2)
    by = {}
    for a in news:
        if any(k in (a.get('desc') or '') for k in RELEVANT):
            by.setdefault(a['symbol'], []).append(a)
    folder = OUT/'dossiers'; folder.mkdir(parents=True, exist_ok=True)
    for _, r in finalists.iterrows():
        (folder/f"{r['symbol']}.md").write_text(dossier(r, ind.loc[r['industry']] if r['industry'] in ind.index else None,
                                                        by.get(r['symbol'], []), session), encoding='utf-8')
    pool['finalist'] = pool['symbol'].isin(finalists['symbol'])
    pool.to_csv(OUT/'stage2.csv', index=False)
    return pool, finalists, ind


def dossier(r, ind, filings, session):
    f = lambda k, n=1: '' if pd.isna(r.get(k)) or r.get(k) is None else (f'{r[k]:.{n}f}' if isinstance(r[k], (int, float)) else str(r[k]))
    lines = [f"# {r['symbol']} — {r['name']} ({r['industry']})", f'Evidence dossier generated {session} by Stage 2. Numbers are CALCULATIONS from Yahoo Finance data; filings are FACTS from NSE.', '',
             f"Stage 1 score {f('stage1_score')} · Stage 2 score {f('stage2_score')} · score 20 sessions ago {f('score_20s_ago')} · 60 sessions ago {f('score_60s_ago')}",
             f"Price ₹{f('close', 2)} · 12-month return {f('ret_12m_pct')}% · {f('from_high_pct')}% from 52-week high · RS rank {f('rs_rank')} · stage-2 trend {r['stage2_trend']} · turnover ₹{f('turnover_cr', 2)} cr/day", '',
             '## Earnings (latest quarter vs same quarter last year)',
             f"Revenue YoY {f('rev_yoy')}% · QoQ {f('rev_qoq')}% (previous QoQ {f('rev_qoq_prev')}%) · quarters of sequential growth in last 4: {f('rev_up_quarters', 0)}",
             f"EBITDA YoY {f('ebitda_yoy')}% · EBITDA margin {f('ebitda_margin')}% (change {f('ebitda_margin_change')} pts) · incremental EBITDA margin {f('incremental_ebitda_margin')}%",
             f"PAT YoY {f('pat_yoy')}% · PAT margin {f('pat_margin')}% · EPS YoY {f('eps_yoy')}% · turnaround {r.get('turnaround')}",
             f"One-off share of EBITDA {f('one_off_share')}% · unusual items share of PBT {f('unusual_share_of_pbt')}% · tax rate {f('tax_rate')}%", '',
             '## Cash flow and balance sheet (latest fiscal year)',
             f"CFO/PAT {f('cfo_to_pat', 2)} · class: {r.get('cash_flow_class')} · receivables growth {f('receivables_growth')}% vs revenue {f('annual_rev_growth')}% · inventory growth {f('inventory_growth')}% · receivable days {f('receivable_days', 0)}",
             f"Net debt/EBITDA {f('net_debt_to_ebitda', 2)} · interest cover {f('interest_cover')} · dilution {f('dilution_pct')}% · ROE {f('roe')}% · EBITDA/invested capital {f('roce_proxy')}%", '',
             '## Valuation',
             f"Market cap ₹{f('market_cap_cr', 0)} cr · TTM P/E {f('pe')} · PEG {f('peg', 2)} · EV/EBITDA {f('ev_to_ebitda')} · EPS growth minus 12-month price return {f('expectation_gap')} pts", '',
             '## Industry (same NSE industry, this scan)']
    if ind is not None:
        lines.append(f"{int(ind['peers'])} peers · {ind['share_rev_growing_20']*100:.0f}% growing revenue >20% · {ind['share_margin_up']*100:.0f}% expanding EBITDA margin · median revenue YoY {ind['median_rev_yoy']:.1f}%")
    lines += ['', f"Flags: {r.get('flags') or 'none'}", '', '## Recent relevant NSE filings (newest first)']
    for a in sorted(filings, key=lambda a: str(a.get('time')), reverse=True)[:15]:
        lines.append(f"- {str(a.get('time'))[:10]} · {a.get('desc')} · {a.get('text', '')[:200]} · {a.get('url') or ''}")
    lines += ['', 'Not available from free data: consensus estimates and revisions, order-book size, capacity and utilization, promoter pledges. Stage 3 must source these from filings, presentations and credible reports, or mark them unknown.']
    return '\n'.join(lines)+'\n'
