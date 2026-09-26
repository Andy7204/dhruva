"""Read-only paper research display with freshness and one recorded NAV."""
from pathlib import Path
import streamlit as st
import pandas as pd
from dhruva.health import inspect
from dhruva.presentation import forward_rows, portfolio_rows

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Dhruva', page_icon='🪷', layout='wide')


@st.fragment(run_every='60s')
def render(root=ROOT):
    health = inspect(root)
    st.title('Dhruva · paper research')
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
    st.subheader('Daily paper calls and portfolio')
    st.caption('Evaluated after the market closes, normally 18:30 IST on weekdays. BUY/SELL are paper orders for the next eligible open; HOLD means no new trade. Closed-market days do not create new signals.')
    if health['status']=='UNHEALTHY':
        st.warning('Calls below are saved historical records, not current conclusions; resolve the reported errors first.')
    for book in health['books']:
        state=book['state']; pending=[o for o in state['orders'] if o['status']=='scheduled']
        action=', '.join(sorted({o['side'] for o in pending})) if pending else 'HOLD'
        st.write(f"**{book['name'].title()} — {action} · {book['as_of']}**")
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
                st.line_chart(frame.set_index('Date')[['Paper index','Nifty price index']])
                st.caption('Both series start at 100 at the labelled starting point. Nifty is a price-only, untaxed, cost-free reference, not an investable total-return comparison. Paper NAV includes modeled costs/tax but excludes unverified income. A few days cannot establish effectiveness; this record accumulates with each daily run.')
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
