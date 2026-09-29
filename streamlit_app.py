"""Read-only paper research display with freshness and one recorded NAV."""
from pathlib import Path
import streamlit as st
import pandas as pd
from dhruva.health import inspect
import json
from dhruva.presentation import forward_rows, portfolio_rows, success_status

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Dhruva', page_icon='🪷', layout='wide')


@st.fragment(run_every='60s')
def render(root=ROOT):
    st.title('Dhruva · paper research')
    with st.spinner('Checking saved books and event history…'):
        health = inspect(root,verify_snapshots=False)
    if health['status'] == 'UNHEALTHY':
        st.error('SYSTEM UNHEALTHY — records may be stale or incomplete. No current strategy conclusion is certified.')
    elif health['status']=='OPERATIONAL':
        st.success('Daily paper engine operational — latest completed session recorded. Model limitations below still apply.')
    else:
        st.warning('Paper records available; accounting or operational verification is incomplete.')
    for problem in health['problems']: st.error(problem)
    for warning in health['warnings']: st.warning(warning)
    st.subheader('Update status')
    success = health['last_success']; attempt = health['last_attempt']
    st.write('Last completed pipeline: '+(success['ended_at'] if success else 'Not yet recorded by the hardened pipeline'))
    st.write('Latest pipeline attempt: '+(f"{attempt.get('ended_at') or attempt.get('started_at')} — {attempt['status']}" if attempt else 'Unknown'))
    st.write('Latest benchmark data: '+str(health['market_date'] or 'Unavailable'))
    st.write('Expected completed market session: '+str(health['expected_date'] or 'Calendar unavailable'))
    st.write('Recorded portfolio date: '+str(health['portfolio_date'] or 'Unavailable'))
    st.write('Strategy: Dhruva v'+health['strategy_version']+' · PAPER ONLY')
    st.code('Deployment commit: '+health['git_commit'], language=None)
    st.caption('This page verifies the event chain and saved balances. Full historical input snapshots are checked by the daily pipeline and watchdog, not decompressed again on every page refresh.')
    if success: st.caption('Source commit: '+success['git_commit']+' · Excluded symbols cannot receive new orders.')
    st.subheader('Recorded v1 portfolio')
    if health['total'] is not None:
        basis='after modeled tax reserve' if health.get('accounting') else 'before tax'
        first, second, third = st.columns(3)
        first.metric('Recorded value '+basis, f"₹{health['total']:,.2f}")
        second.metric('Recorded return '+basis, f"{(health['total']/health['starting_capital']-1)*100:+.2f}%")
        third.metric('Starting paper capital', f"₹{health['starting_capital']:,.0f}")
        st.caption('One set of saved book observations; totals are not revalued from newer cached quotes.')
        st.table([{'Book': b['name'], 'Date': b['as_of'], 'Recorded value '+basis+' (INR)': b['value'],
                   'Starting capital (INR)': b['capital']} for b in health['books']])
    else: st.error('Portfolio totals withheld: every configured book must be valid. Partial totals would be misleading.')
    st.subheader('Income estimate — assumption only')
    st.caption('LIQUIDBEES scenario: 4% simple annual income on ₹1,000 per prior-close settled unit, ACT/365 including weekends; configured slab tax, surcharge and cess, no reinvestment. Accrues from the September30, 2026 close. This is not a yield forecast, verified receipt, spendable balance or recorded NAV. Unknown actual credits and withholding remain excluded.')
    st.caption('Idle cash scenario: the same 4% simple annual rate and tax on prior-close settled cash, as if parked in a liquid fund. Also from the September30 close, also outside recorded NAV.')
    estimates=[{'Book':b['name'], 'Scenario':label, 'Through':b['state'][key]['as_of'],
                'Assumed gross (INR)':round(b['state'][key]['gross'],2),
                'Assumed tax (INR)':round(b['state'][key]['tax'],2),
                'Assumed net (INR)':round(b['state'][key]['net'],2)}
               for b in health['books'] for key,label in (('income_scenario','LIQUIDBEES units'),('cash_yield_scenario','Idle cash'))
               if b['state'].get(key)]
    if estimates: st.table(estimates)
    else: st.write('No prospective income estimate recorded yet; it begins with the next eligible daily evaluations.')
    st.subheader('Daily paper calls and portfolio')
    st.caption('Evaluated after the market closes, normally 18:30 IST on weekdays. BUY/SELL are paper orders for the next eligible open; HOLD means no new trade. Closed-market days do not create new signals.')
    if health['status']=='UNHEALTHY':
        st.warning('Calls below are saved historical records, not current conclusions; resolve the reported errors first.')
    for book in health['books']:
        state=book['state']; pending=[o for o in state['orders'] if o['status']=='scheduled']
        action=', '.join(sorted({o['side'] for o in pending})) if pending else 'HOLD'
        changed=max([d for o in state['orders'] for d in (o.get('decided_date'),o.get('fill_date')) if d] or [state.get('inception') or 'start'])
        st.write(f"**{book['name'].title()} — {action} · {book['as_of']}**"+('' if pending else f" · no change since {changed}"))
        st.write(('Market filter permits stock entries.' if state.get('risk_on') else
                  'Market filter is defensive: new stock entries are restricted; existing positions follow exit rules.')+
                 (' Circuit breaker is active.' if state.get('breaker') else '')+
                 f" Next regular allocation review in {state.get('next_rebalance_in','unknown')} trading sessions. Stops are checked daily.")
        st.caption(f"Cash ₹{state['cash']:,.2f} · Tax reserve ₹{state.get('tax_reserve',0):,.2f} · Unsettled sale proceeds ₹{sum(r['amount'] for r in state.get('receivables',[])):,.2f}")
    holdings,orders=portfolio_rows(health['books'])
    if holdings: st.dataframe(holdings, hide_index=True, use_container_width=True)
    else: st.write('No holdings available.')
    with st.expander('Permanent paper order journal'):
        if orders: st.dataframe(orders,hide_index=True,use_container_width=True)
        else: st.write('No paper orders recorded.')
    st.subheader('How the strategy works')
    st.write('Dhruva ranks eligible Nifty-500 stocks by past 12-month momentum. A 200-day market trend filter restricts stock buying in weak markets. The 70% balanced core and 30% aggressive book share that filter but use different defensive allocations. Gold, silver, liquid funds and cash can reduce equity exposure; they are not guaranteed protection.')
    st.write('Both books review allocations every 63 trading sessions. Each completed session still updates prices, fills eligible prior orders, checks stops and the drawdown circuit breaker, and records BUY, SELL or HOLD. A trend recovery does not guarantee an immediate purchase. This approach can miss rebounds and lose during choppy markets. It is not a buy-at-the-bottom strategy.')
    st.caption('Costs, slippage, settlement restrictions and modeled shared tax reserve affect paper balances. Tax assumptions are simplified. AI may explain a call; it cannot choose trades.')
    st.subheader('Forward paper performance')
    if health.get('ledger') and health['total'] is not None and not any('LEDGER' in p for p in health['problems']):
        try:
            rows=forward_rows(root)
            if rows:
                frame=pd.DataFrame(rows)
                st.line_chart(frame.set_index('Date')[['Paper index','Paper index + assumed income','NIFTYBEES total-return index','Nifty price index']])
                st.caption('All series start at 100 at the labelled starting point. NIFTYBEES is the fair benchmark: an investable Nifty 50 ETF whose price keeps constituent dividends, so it tracks the Total Return Index less a small fee. It is shown before any tax an investor would pay on selling. The Nifty price index omits dividends and flatters the strategy by about 1.3% a year. Paper NAV includes modeled costs/tax; the "+ assumed income" line adds the 4% scenarios above and is not recorded NAV. Missing NIFTYBEES values are vendor gaps, not zero. A few days cannot establish effectiveness.')
                criteria=json.loads((root/'config.json').read_text(encoding='utf-8')).get('success_criteria')
                if criteria:
                    verdict=success_status(rows,criteria)
                    st.subheader('Does it work? Pre-registered test')
                    st.write(f"**{verdict['verdict']}** — {verdict['reason']}")
                    st.write(f"Rule, fixed in advance: after at least {criteria['earliest_verdict_years']} years, recorded paper NAV must beat NIFTYBEES by at least "
                             f"{criteria['pass_min_excess_cagr_pct']:.1f} percentage points a year, with worst drawdown under {criteria['max_drawdown_limit_pct']:.0f}%. "
                             f"It fails early if drawdown breaches that limit, or if after {criteria['early_fail_after_years']} year it trails NIFTYBEES by "
                             f"{criteria['early_fail_cumulative_shortfall_pct']:.0f} points or more; final verdict at {criteria['final_verdict_years']} years. Assumed income never counts.")
                    if verdict.get('through'):
                        st.caption(f"Progress {verdict['start']} to {verdict['through']} ({verdict['years']:.2f} years): paper {verdict['paper_return_pct']:+.2f}%, "
                                   f"NIFTYBEES {verdict['benchmark_return_pct']:+.2f}%, worst paper drawdown {verdict['worst_drawdown_pct']:.2f}%. "
                                   '[Criteria and change log](https://github.com/Andy7204/dhruva/blob/main/docs/SUCCESS_CRITERIA.md)')
                st.dataframe(frame,hide_index=True,use_container_width=True)
                st.download_button('Download dated performance records',frame.to_csv(index=False),'dhruva_forward.csv','text/csv')
        except (ValueError,KeyError,OSError,TypeError) as exc:
            st.error('Forward history unavailable: '+str(exc))
    else: st.write('Forward chart withheld until ledger and portfolio evidence are available.')
    st.subheader('Historical backtest — separate research simulation')
    st.warning('Retrospective challenge study, not an exact replay of today’s repaired live engine. Uses current constituents (survivorship bias), adjusted-price research units, simplified tax and execution assumptions. Results are not a forecast or a validated live return.')
    score=root/'research/results/scorecard.csv'
    if score.exists():
        table=pd.read_csv(score,index_col=0)
        table.index=table.index.map(lambda s:{
            'current_200_63':'Current policy: 200-day trend / 63-session review',
            'faster_100_63':'100-day trend / 63-session review',
            'faster_50_63':'50-day trend / 63-session review',
            'monthly_200_21':'200-day trend / monthly review',
            'crossing_200_63':'200-day trend / extra crossing reviews',
            'no_market_gate_63':'No market trend filter',
            'core_plus_dip':'70% current core + 30% dip buying',
            'core_plus_index':'70% current core + 30% index holding',
            'index_hold':'NIFTYBEES buy and hold',
            'index_dip':'Staged NIFTYBEES dip buying'}.get(s.split('/')[-1],s))
        st.caption('Existing study: 3 October 2022–15 September 2026. Returns include modeled research costs/tax and terminal liquidation. No best-performing variant was automatically deployed.')
        st.dataframe(table[['return_pct','cagr_pct','max_drawdown_pct','fees_rupees','tax_rupees','trades']].rename(columns={
            'return_pct':'Return %','cagr_pct':'Annualized return %','max_drawdown_pct':'Worst drawdown %',
            'fees_rupees':'Fees INR','tax_rupees':'Tax INR','trades':'Fills'}),use_container_width=True)
        st.markdown('[Read the existing study, dip-buying comparisons and limitations](https://github.com/Andy7204/dhruva/blob/main/research/results/REPORT.md)')
    st.subheader('Methodology and evidence')
    st.markdown('[Audit](https://github.com/Andy7204/dhruva/blob/main/docs/CURRENT_STATE_AUDIT.md) · '
                '[Verified progress](https://github.com/Andy7204/dhruva/blob/main/docs/HARDENING_PROGRESS.md) · '
                '[Frozen v1](https://github.com/Andy7204/dhruva/tree/main/strategies/dhruva_v1)')
    st.write('Historical simulations are separate from forward paper observations. Original historical results contain the limitations documented in the audit.')
    st.caption('Educational paper research only. No real orders. Health refreshes every 60 seconds while this page is active. '
               'Weekday scheduling is nominal; missed or delayed jobs are not a no-signal conclusion.')


render()
