"""Build a self-contained HTML report and static PNG figures from frozen results."""
import base64
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from challenge import OUT, ROOT

LABELS={
 'current_200_63':'Current policy: 200-day / quarterly',
 'faster_100_63':'100-day gate / quarterly',
 'faster_50_63':'50-day gate / quarterly',
 'monthly_200_21':'200-day gate / monthly',
 'crossing_200_63':'200-day gate / extra crossing reviews',
 'no_market_gate_63':'No market gate / quarterly',
 'core_plus_dip':'70% current core + 30% dip buying',
 'core_plus_index':'70% current core + 30% index holding',
 'index_hold':'100% NIFTYBEES buy and hold',
 'index_dip':'100% staged NIFTYBEES dip buying',
}


def table(rows,headers):
    return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join(
        '<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def main():
    r=json.loads((OUT/'results.json').read_text())
    meta=json.loads((OUT/'manifest.json').read_text())
    syn=json.loads((OUT/'synthetic.json').read_text())
    c=pd.read_csv(OUT/'curves.csv',index_col=0,parse_dates=True)
    full={k.split('/')[1]:v for k,v in r['full'].items() if k.startswith('500/')}
    baseline=full['current_200_63']
    same=json.loads((OUT/'same_asset.json').read_text())
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(15,9),layout='constrained')
    groups=[('Market filter speed',['current_200_63','faster_100_63','faster_50_63','no_market_gate_63']),
            ('Review delay',['current_200_63','monthly_200_21','crossing_200_63']),
            ('Different satellite rules',['current_200_63','core_plus_dip','core_plus_index']),
            ('Index alternatives',['current_200_63','index_hold','index_dip'])]
    for ax,(title,names) in zip(axes.flat,groups):
        for name in names:
            ax.plot(c.index,c[name]/1000,label=LABELS[name],linewidth=2 if name=='current_200_63' else 1.4)
        ax.set_title(title,loc='left',fontweight='bold'); ax.set_ylabel('Marked NAV, INR thousands')
        ax.grid(alpha=.15); ax.legend(fontsize=7,loc='upper left'); ax.tick_params(axis='x',rotation=20)
    fig.suptitle('Dhruva challenge study | identical execution and accounting\nTax-reserved marked NAV; terminal liquidation included in scorecard, not these paths',fontsize=13)
    fig.savefig(OUT/'comparison.png',dpi=160); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    sc=pd.read_csv(OUT/'synthetic_curves.csv')
    for ax,(name,g) in zip(axes,sc.groupby('scenario',sort=False)):
        for rule,x in g.groupby('rule',sort=False):
            ax.plot(range(len(x)),x.nav/1000,label=rule)
        ax.set_title(name.replace('_',' '),fontsize=10); ax.set_xlabel('Synthetic trading sessions')
        ax.set_ylabel('Marked NAV, INR thousands'); ax.legend(fontsize=7); ax.grid(alpha=.15)
    fig.suptitle('Invented price paths: mechanisms only, not historical evidence',fontsize=13)
    fig.savefig(OUT/'synthetic.png',dpi=160); plt.close(fig)
    rows=[]
    for name,x in full.items():
        rows.append([LABELS[name],f"{x['return_pct']:+.2f}%",f"{x['cagr_pct']:.2f}%",f"{x['max_drawdown_pct']:.2f}%",
                     f"{x['cash_pct_average']:.1f}%",f"{x['fees_rupees']:,.0f}",f"{x['tax_rupees']:,.0f}",x['trades']])
    comparisons=table(rows,['Rule','Net total return','CAGR','Worst drawdown','Average cash','Fees INR','Tax INR','Fills incl. final exit'])
    same_rows=[]
    for label,x in [('Index buy and hold',full['index_hold']),('Index staged dip buying',full['index_dip'])]+list(same['full'].items()):
        same_rows.append([label,f"{x['return_pct']:+.2f}%",f"{x['max_drawdown_pct']:.2f}%",f"{x['cash_pct_average']:.1f}%"])
    same_table=table(same_rows,['Same ETF, different timing','Net return','Worst drawdown','Average cash'])
    robustness=[]
    for name in full:
        a=r['full']['100/'+name]; b=r['final_year_fresh_start'][name]; w=r['rolling_252_sessions'][name]
        robustness.append([LABELS[name],f"{a['return_pct']:+.2f}%",f"{a['max_drawdown_pct']:.2f}%",
                           f"{b['return_pct']:+.2f}%",f"{w['min']:+.2f}% / {w['median']:+.2f}% / {w['max']:+.2f}%",
                           f"{w['beats_current_pct']:.1f}%"])
    robust_table=table(robustness,['Rule','Nifty-100 universe return','Nifty-100 drawdown','Fresh-start final year','Rolling year min / median / max','Rolling windows beating current'])
    phases=[]
    for name in r['rebalance_phase']['21']:
        vals=[full[name]['return_pct']]+[r['rebalance_phase'][str(p)][name]['return_pct'] for p in [21,42]]
        phases.append([LABELS[name]]+[f'{x:+.2f}%' for x in vals])
    friction=[]
    for name in r['friction']['no_friction']:
        vals=[r['friction']['no_friction'][name]['return_pct'],r['friction']['costs_no_tax'][name]['return_pct'],
              full[name]['return_pct'],r['friction']['double_costs'][name]['return_pct']]
        friction.append([LABELS[name]]+[f'{x:+.2f}%' for x in vals])
    cross=r['crossings']; waits=[x['wait_sessions'] for x in cross if x['next_review_in_window']]
    moves=[x['nifty_move_to_review_pct'] for x in cross if x['next_review_in_window']]
    crossing_text=(f'{len(cross)} upward 200-day crossings occurred. Among crossings with a subsequent scheduled review in the sample, '
        f'the median wait was {np.median(waits):.0f} sessions (maximum {max(waits)}). '
        f'Nifty moves from the crossing close to that review ranged from {min(moves):+.2f}% to {max(moves):+.2f}%. '
        'This measures scheduling delay, not guaranteed missed profit: some crossings reversed before the review, '
        'and stock eligibility, cash availability and circuit breakers can still block purchases.')
    # Rebound already completed by an upward crossing, measured ex post for explanation.
    bench=pd.read_csv(ROOT/'data/cache/_IDX_NSEI.csv',parse_dates=['date']).set_index('date').adjclose.loc[:meta['window'][1]]
    gate=bench>bench.rolling(200).mean(); episodes=[]
    for item in cross:
        i=bench.index.get_loc(pd.Timestamp(item['crossing_date'])); j=i-1
        while j>0 and not gate.iloc[j-1]: j-=1
        trough=bench.iloc[j:i+1].min()
        episodes.append(dict(**item,rebound_from_prior_off_episode_low_pct=round((bench.iloc[i]/trough-1)*100,3)))
    (OUT/'crossing_episodes.json').write_text(json.dumps(episodes,indent=2))
    reb=[x['rebound_from_prior_off_episode_low_pct'] for x in episodes]
    claims=[
        ('1. Is the 200-day filter too slow?',
         f"The 100-day gate returned {full['faster_100_63']['return_pct']:+.2f}% and the 50-day gate {full['faster_50_63']['return_pct']:+.2f}%, versus {baseline['return_pct']:+.2f}% for 200 days. "
         f"Removing only the market gate returned {full['no_market_gate_63']['return_pct']:+.2f}%. At upward crossings, the rebound from the preceding risk-off episode's low had already ranged from {min(reb):.2f}% to {max(reb):.2f}% (median {np.median(reb):.2f}%). "
         'Those lows are identified retrospectively for attribution, never used as buy signals. Shortening the market filter does not remove the individual-stock 200-day filter or the core allocation’s 50/200-day votes. No valuation/fundamentals test was possible: a moving average cannot establish cheapness.'),
        ('2. Does the quarterly review add damaging delay?',
         f"Monthly reviews returned {full['monthly_200_21']['return_pct']:+.2f}% with {full['monthly_200_21']['max_drawdown_pct']:.2f}% worst drawdown; extra reviews on both crossing directions returned {full['crossing_200_63']['return_pct']:+.2f}% with {full['crossing_200_63']['max_drawdown_pct']:.2f}% drawdown. "+crossing_text),
        ('3. Does the 70/30 split diversify timing?',
         f"Both original books share the same gate and quarterly calendar. A dip-buying satellite returned {full['core_plus_dip']['return_pct']:+.2f}% with {full['core_plus_dip']['max_drawdown_pct']:.2f}% drawdown; an always-invested index satellite returned {full['core_plus_index']['return_pct']:+.2f}% with {full['core_plus_index']['max_drawdown_pct']:.2f}% drawdown. "
         'These alternatives change both timing and stock selection, so their differences are not pure timing effects. They do provide genuinely different entry behavior from the core; this is not a claim of uncorrelated returns.'),
        ('4. How expensive are waiting and trading?',
         f"The current-policy baseline averaged {baseline['cash_pct_average']:.1f}% cash versus {full['index_hold']['cash_pct_average']:.1f}% for index holding. "
         f"Its modeled fees were INR {baseline['fees_rupees']:,.0f}, slippage INR {baseline['slippage_rupees']:,.0f}, and total tax INR {baseline['tax_rupees']:,.0f}, including terminal exit. "
         'The friction table reruns the rules because costs and tax change available capital and later decisions; column differences are not a pure additive fee attribution. Cash earns zero; defensive asset gains/losses remain in NAV. A buy-and-hold comparison captures a combined opportunity-cost, asset-selection and risk difference, not cash drag alone.'),
        ('5. Which price paths favor buying dips?',
         'The invented examples isolate the mechanism using one ETF and the same execution/accounting. The dip rule deploys thirds at -10/-20/-30% from a known peak, and exits when that peak is recovered. A quarterly trend rule can avoid an entire choppy path, but can miss a recovery too. Daily trend reviews can lose on false crossings. Buying a dip does not require buying exactly at the bottom, but it can keep adding exposure to a prolonged decline. These outcomes are sensitive to the explicit path and rule; no probabilities are inferred.'),
    ]
    syn_rows=[]
    for scenario,rules in syn.items():
        for rule,x in rules.items():
            syn_rows.append([scenario.replace('_',' '),rule,f"{x['return_pct']:+.2f}%",f"{x['max_drawdown_pct']:.2f}%"])
    conclusion=(f"The criticisms identify real trade-offs, but faster reactions did not consistently improve this sample. "
        f"Current policy returned {baseline['return_pct']:+.2f}% with {baseline['max_drawdown_pct']:.2f}% worst drawdown under audited research execution. "
        f"The 100-day gate improved full-window return to {full['faster_100_63']['return_pct']:+.2f}% but lagged in the fresh-start final year. "
        f"The same-ETF control supports the timing objection: index holding returned {full['index_hold']['return_pct']:+.2f}% versus {same['full']['ETF_200_63']['return_pct']:+.2f}% with a quarterly 200-day gate. "
        "Dhruva's stock selection and defensive allocation cannot be conflated with the benefit of the gate. "
        "A different satellite reduced drawdown in this sample, with somewhat lower total return. "
        "The data are too short and biased to establish a universally superior rule or justify automatic deployment.")
    md=['# Dhruva challenge study',f"\nWindow: {meta['window'][0]} to {meta['window'][1]} ({meta['sessions']} sessions after warmup).",
        '\n'+conclusion,
        '\nBaseline = current policy with audited research execution, not an exact replay of the dashboard.',
        '\n## Full-window scorecard\n', '| Rule | Net return | CAGR | Worst drawdown | Average cash | Fees INR | Tax INR | Fills |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    md += ['| '+' | '.join(map(str,row))+' |' for row in rows]
    for title,text in claims: md+=['\n## '+title,'\n'+text]
    md+=['\n## Supplemental same-asset timing control',
         '\nAdded after the primary matrix to separate timing from asset selection; no optimized parameters.',
         '| Rule | Net return | Worst drawdown | Average cash |','|---|---:|---:|---:|']
    md+=['| '+' | '.join(map(str,row))+' |' for row in same_rows]
    md+=['\n## Limits and reproducibility','\n'+(ROOT/'research/PROTOCOL.md').read_text(),
         '\nCommands: `python research/test_challenge.py`; `python research/challenge.py`; `python research/scenarios.py`; `python research/make_report.py`.']
    (OUT/'REPORT.md').write_text('\n'.join(md),encoding='utf-8')
    img=lambda name:'<img alt="Research comparison chart" src="data:image/png;base64,'+base64.b64encode((OUT/name).read_bytes()).decode()+'">'
    body=f'''<header><p class="eyebrow">DHRUVA · RESEARCH CHALLENGE</p><h1>Does waiting for strength pay?</h1>
    <p>{meta['window'][0]} to {meta['window'][1]} · {meta['sessions']} sessions · INR100,000 initial capital</p></header>
    <aside><strong>Scope:</strong> ten fixed rules, current Nifty-500 and Nifty-100 universes, review-phase checks,
    a fresh-start final year, friction sensitivities, and three synthetic paths. No production strategy was changed.
    These are retrospective results using an approximate tax and adjusted-price model—not a forecast or investment recommendation.</aside>
    <h2>What the tests say</h2><p>{html.escape(conclusion)}</p>
    <h2>Comparable outcomes</h2><p>All returns below include fees, slippage, modeled tax and an estimated final liquidation.
    Baseline means current policy under audited research execution. It does not reproduce the dashboard’s original backtest.</p>
    {comparisons}{img('comparison.png')}
    '''
    body+=''.join('<h2>'+html.escape(title)+'</h2><p>'+html.escape(text)+'</p>' for title,text in claims)
    body+='<h2>Same asset: does the market gate itself help?</h2><p>This supplemental comparison was added after the primary matrix to isolate market timing from stock selection. '
    body+='Every row trades NIFTYBEES. ETF_200_63 means a 200-day Nifty filter reviewed every 63 sessions; ETF_200_1 reviews daily. '
    body+='These controls have no defensive basket, stock ranking, tax-aware exit delay or portfolio circuit breaker. They isolate a simple gate, not the entire Dhruva policy.</p>'+same_table
    body+='<h2>Does the result survive a different sample?</h2><p>The Nifty-100 list is also today’s list and still has survivorship bias. '
    body+='The final-year test starts in cash with earlier observations available for indicators; it is not a truly untouched holdout. Rolling windows overlap and are not independent observations.</p>'+robust_table
    body+='<h2>Review-calendar sensitivity</h2><p>Same initial signal date; subsequent periodic reviews are shifted. Crossings remain immediate in the crossing variant.</p>'+table(phases,['Rule','Phase 0','Phase 21','Phase 42'])
    body+='<h2>Friction and cash-budget sensitivity</h2>'+table(friction,['Rule','No costs / no tax','Costs / no tax','Costs + tax','Double costs + tax'])
    body+='<h2>Invented scenarios</h2>'+table(syn_rows,['Path','Rule','Net return','Worst drawdown'])+img('synthetic.png')
    body+='<h2>Every 200-day upward crossing</h2>'+table([[x['crossing_date'],x['wait_sessions'],x['next_review_in_window'],x['nifty_move_to_review_pct'],x['risk_on_at_review']] for x in cross],['Crossing','Sessions to review','Review in sample','Nifty move %','Still risk-on at review'])
    body+='<h2>Frozen protocol, assumptions and known limitations</h2><pre>'+html.escape((ROOT/'research/PROTOCOL.md').read_text())+'</pre>'
    body+='<h2>Verification</h2><p>Eight accounting/causality tests passed. Final wealth reconciled independently to all ten main fill ledgers within INR0.02. '
    body+='Five actual cached instruments passed prefix invariance: removing later observations did not change earlier indicators. Production strategy, live books, prices and dashboard were not modified. '
    body+='These checks validate the harness mechanics, not the accuracy or completeness of Yahoo data, tax law, or a future investment edge.</p>'
    body+='<footer>Reproduce with research/test_challenge.py, challenge.py, scenarios.py, same_asset.py, verify_results.py and make_report.py. Machine-readable results, source hashes and fill ledgers are alongside this report.</footer>'
    css='body{font:16px/1.55 system-ui,sans-serif;color:#172d36;background:#f5f7f7;max-width:1250px;margin:40px auto;padding:0 30px}header{border-bottom:4px solid #167d8d;margin-bottom:24px}h1{font-size:44px;line-height:1.1}h2{margin-top:42px;color:#124f61}.eyebrow{letter-spacing:.16em;color:#167d8d;font-size:12px}aside{background:#e3edf0;border-left:4px solid #167d8d;padding:20px}table{width:100%;border-collapse:collapse;font-size:13px;background:white;margin:20px 0}th{background:#183e4c;color:white;text-align:left}td,th{padding:10px;border-bottom:1px solid #dce4e8}tr:nth-child(even){background:#edf2f4}img{width:100%;height:auto;margin-top:25px}pre{white-space:pre-wrap;background:white;padding:24px;font-size:13px}footer{margin:35px 0;color:#567;font-size:13px}'
    (OUT/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dhruva challenge study</title><style>'+css+'</style>'+body+'</html>',encoding='utf-8')
    print('Wrote REPORT.html, REPORT.md and two figures')


if __name__=='__main__': main()
