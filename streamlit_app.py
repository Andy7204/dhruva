"""Dhruva v2 — read-only view of saved paper books and research. Never recalculates trades."""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
NAMES = {'MIDMOM50': 'Midcap150 Momentum 50', 'MOM30': 'Nifty200 Momentum 30', 'GOLD': 'Gold',
         'NDX': 'Nasdaq-100', 'LIQ': 'Liquid fund', 'N50': 'Nifty 50'}
HOW = {
    'A': 'Holds 70% in the Nifty Midcap150 Momentum 50 index and 30% in gold. Rebalances back to 70/30 once a year. Momentum picks midcaps that rose most over 6 and 12 months; gold cushions equity crashes.',
    'B': 'Holds 60% Nifty200 Momentum 30, 20% gold and 20% Nasdaq-100 (in rupees). Rebalances once a year. The most diversified book: large-cap momentum, a crash hedge and a foreign growth market.',
    'C': 'Every 21 sessions, scores Momentum 30, Midcap Momentum 50, Nasdaq-100 and gold by the average of their 1-, 3- and 6-month returns and holds only the best one. If even the best is negative, it holds a liquid fund. Backtest 13.4–18.8% a year depending only on which week it reviews, so its edge is fragile; it also pays more short-term tax.',
}


def read(path):
    try:
        return json.loads((ROOT/path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def mix(weights):
    return ', '.join(f'{NAMES.get(a, a)} {w*100:.0f}%' for a, w in sorted(weights.items(), key=lambda x: -x[1]) if w > .005) or 'Cash'


def radar():
    st.caption('Three-stage funnel over about 750 NSE stocks (Nifty 500 + Microcap 250). Stage 1 scores every company on '
               'measurable fundamentals; Stage 2 narrows to 10 using industry-wide inflection, score momentum and filings; '
               'Stage 3 has Claude underwrite those 10 with your framework. Paper research, not investment advice.')
    rep = ROOT/'runs/inflection/report.md'
    if rep.exists():
        st.markdown(rep.read_text(encoding='utf-8').split('
', 1)[1])
    status = read('runs/inflection/underwriter_status.json') or {}
    for e in status.get('errors', []):
        st.warning(e)
    s2 = ROOT/'runs/inflection/stage2.csv'
    if s2.exists():
        st.subheader('Stage 2 pool (top 50 from Stage 1)')
        t = pd.read_csv(s2)
        cols = [c for c in ['symbol', 'name', 'industry', 'finalist', 'stage2_score', 'stage1_score', 'industry_score', 'score_change_20s',
                            'rev_yoy', 'ebitda_yoy', 'pat_yoy', 'incremental_ebitda_margin', 'cfo_to_pat', 'pe', 'peg',
                            'expectation_gap', 'market_cap_cr', 'orders_90d', 'capacity_90d', 'legal_or_regulatory_90d', 'flags'] if c in t]
        st.dataframe(t[cols], hide_index=True, width='stretch')
    s1 = ROOT/'runs/inflection/stage1.csv'
    if s1.exists():
        full = pd.read_csv(s1)
        st.download_button(f'Download all {len(full)} Stage 1 scores (CSV)', full.to_csv(index=False), 'stage1.csv', 'text/csv')
    st.markdown('[How the framework works and its limits](https://github.com/Andy7204/dhruva/blob/main/docs/MULTIBAGGER.md)')


def render():
    st.set_page_config(page_title='Dhruva', page_icon='🪷', layout='wide')
    st.title('Dhruva · index strategy paper lab')
    st.caption('Paper-only forward test of three deterministic index strategies against Nifty 50. '
               'Educational research, not investment advice. No real orders.')
    cfg = read('config.v2.json')
    status = read('runs/status.json') or {}
    state = read('runs/forward/state.json')

    try:
        from dhruva.calendar import expected_date
        expected = expected_date()
    except Exception as exc:  # calendar coverage problems must be visible
        expected = None; st.error(f'Calendar: {exc}')
    as_of = min(b['as_of'] for b in state.values()) if state else None
    if status.get('status') == 'FAILED':
        st.error('Last daily update failed: '+'; '.join(status.get('errors', [])))
    elif state and expected and as_of < expected and expected > cfg['forward_start']:
        st.warning(f'Books recorded through {as_of}; latest completed session is {expected}. The daily update runs after 18:30 IST.')
    elif state:
        st.success(f'Books up to date through {as_of}.')
    else:
        st.info(f"Forward test starts with the {cfg['forward_start']} close. First paper allocations fill at the next session's close.")
    for w in status.get('warnings', []):
        st.warning(w)

    index_tab, radar_tab = st.tabs(['Index strategies', 'Inflection radar (stock research)'])
    with index_tab:
        st.header('Current paper calls')
        if state:
            bench = state.get('N50', {}).get('liquidation_value')
            cols = st.columns(3)
            for col, bid in zip(cols, [b for b in cfg['books']]):
                b = state[bid]
                with col:
                    st.subheader(b['label'])
                    if b.get('pending_target'):
                        st.markdown(f"**REBALANCE at next close →** {mix(b['pending_target'])}")
                    else:
                        nxt = b.get('next_review_in')
                        st.markdown('**HOLD**' + (f' · next review in {nxt} sessions' if nxt else ''))
                    st.write('Holding: '+mix(b['weights']))
                    st.metric('Value after tax (paper)', f"₹{b['liquidation_value']:,.0f}",
                              f"{(b['liquidation_value']/bench-1)*100:+.2f}% vs Nifty 50" if bench else None)
                    st.caption(f"Last decision {b.get('last_decision')} · trades {b['trades']} · costs ₹{b['costs']:,.0f} · tax paid ₹{b['tax_paid']:,.0f}")
        else:
            st.write('No paper allocations yet.')

        st.header('Forward performance')
        from dhruva.forward import history
        hist = history(ROOT)
        if len(hist) >= 2:
            idx = hist/hist.iloc[0]*100
            idx.columns = [(state or {}).get(c, {}).get('label', c) for c in idx.columns]
            import altair as alt
            long = idx.reset_index(names='Date').melt('Date', var_name='Book', value_name='Index (start = 100)')
            st.altair_chart(alt.Chart(long).mark_line().encode(
                x='Date:T', y=alt.Y('Index (start = 100):Q', scale=alt.Scale(zero=False)), color='Book:N'), use_container_width=True)
            from dhruva.performance import summary
            rows = summary(hist, cfg['success_criteria'])
            st.dataframe(pd.DataFrame(rows).set_index('Book'), width='stretch')
            st.caption('Values are after ETF costs and after the tax that selling everything would trigger. '
                       'Annualized figures and ratios appear only after enough history; a few weeks prove nothing.')
        else:
            st.write('The chart starts once two sessions are recorded.')

        st.header('Pre-registered success test')
        c = cfg['success_criteria']
        st.write(f"Each book passes only if, after at least {c['earliest_verdict_years']} years, its after-tax annual return beats Nifty 50 "
                 f"buy-and-hold by {c['pass_min_excess_cagr_pct']:.0f}+ points with worst drawdown under {c['max_drawdown_limit_pct']:.0f}%. "
                 f"It fails early on a deeper drawdown, or if after {c['early_fail_after_years']} year it trails Nifty 50 by "
                 f"{c['early_fail_cumulative_shortfall_pct']:.0f}+ points. Final verdict at {c['final_verdict_years']} years.")

        st.header('How each strategy works')
        for bid, spec in cfg['books'].items():
            st.markdown(f"**{spec['label']}** — {HOW.get(bid, '')}")
        st.caption('Signals use closes up to each day; trades fill at the next close. Costs: ETF expense ratios plus 0.1–0.3% per trade. '
                   'Tax: Indian FIFO capital gains (equity 20%/12.5%, gold and foreign funds 12.5% after two years or 31.2% slab), paid each April.')

        st.header('Backtest evidence (research, not a forecast)')
        score = ROOT/'research/v2/results/scorecard.csv'
        if score.exists():
            table = pd.read_csv(score)
            st.dataframe(table, hide_index=True, width='stretch')
        st.warning('Survivorship-free official NSE Total Return Indices, but factor-index history before each launch date is NSE\'s back-calculation. '
                   'Only the "live" columns use real post-launch data (4–14 years). 24 strategies were tested, so the best look better than their future. '
                   'The 2008 crash causes the deepest drawdowns. Momentum is now widely used and may earn less in future.')
        st.markdown('[Method, data and limits](https://github.com/Andy7204/dhruva/blob/main/research/v2/README.md)')
    with radar_tab:
        radar()
    st.caption(f'Page rendered {datetime.now():%Y-%m-%d %H:%M}. Data: niftyindices.com, Yahoo Finance.')


render()
