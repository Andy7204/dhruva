"""Read-only paper research display with freshness and one recorded NAV."""
from pathlib import Path
import streamlit as st
from dhruva.health import inspect

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Dhruva', page_icon='🪷', layout='wide')


@st.fragment(run_every='60s')
def render(root=ROOT):
    health = inspect(root)
    st.title('Dhruva · paper research')
    if health['status'] == 'UNHEALTHY':
        st.error('SYSTEM UNHEALTHY — records may be stale or incomplete. No current strategy conclusion is certified.')
    else:
        st.warning('SYSTEM DEGRADED — original v1 accounting is under repair. These records are not a validated live track record.')
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
    if success: st.caption('Execution completed; complete-universe data quality is not yet certified. Source commit: '+success['git_commit'])
    st.subheader('Recorded v1 portfolio')
    if health['total'] is not None:
        first, second, third = st.columns(3)
        first.metric('Recorded value before tax', f"₹{health['total']:,.2f}")
        second.metric('Recorded return before tax', f"{(health['total']/health['starting_capital']-1)*100:+.2f}%")
        third.metric('Starting paper capital', f"₹{health['starting_capital']:,.0f}")
        st.caption('One set of saved book observations; totals are not revalued from newer cached quotes.')
        st.table([{'Book': b['name'], 'Date': b['as_of'], 'Recorded value before tax (INR)': b['value'],
                   'Starting capital (INR)': b['capital']} for b in health['books']])
    else: st.error('Portfolio totals withheld: every configured book must be valid. Partial totals would be misleading.')
    st.subheader('Latest recorded paper instructions')
    st.caption('Archived paper intent only. This is not a fresh signal or an instruction to place real orders.')
    alert = root/'runs/alert.txt'
    if alert.exists(): st.text(alert.read_text(encoding='utf-8'))
    else: st.write('No recorded instructions available.')
    st.subheader('Methodology and evidence')
    st.markdown('[Audit](https://github.com/Andy7204/dhruva/blob/main/docs/CURRENT_STATE_AUDIT.md) · '
                '[Verified progress](https://github.com/Andy7204/dhruva/blob/main/docs/HARDENING_PROGRESS.md) · '
                '[Frozen v1](https://github.com/Andy7204/dhruva/tree/main/strategies/dhruva_v1)')
    st.write('Historical simulations are separate from forward paper observations. Original historical results contain the limitations documented in the audit.')
    st.caption('Educational paper research only. No real orders. Health refreshes every 60 seconds while this page is active. '
               'Weekday scheduling is nominal; missed or delayed jobs are not a no-signal conclusion.')


render()
