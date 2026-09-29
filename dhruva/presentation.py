"""Read-only views of saved paper evidence; never recalculate signals or NAV."""
import json
from pathlib import Path


def _cached_closes(root, symbol):
    """Vendor closes by date; fallback for rows recorded before capture began."""
    import csv
    path=Path(root)/'data/cache'/(symbol.replace('^','_IDX_').replace('.','_')+'.csv')
    try:
        with path.open(encoding='utf-8') as stream:
            return {row['date'][:10]:float(row['close']) for row in csv.DictReader(stream) if row.get('close')}
    except (OSError,ValueError,KeyError):
        return {}


def forward_rows(root, tr_symbol='NIFTYBEES.NS'):
    from qlab.income_model import scenario_net
    rows={}
    for path in sorted((Path(root)/'runs/ledger/dhruva_v1/segments').glob('*.json')):
        payload=json.loads(path.read_text(encoding='utf-8'))['payload']
        bundle=payload['state']; events=payload['events']
        if not events or not bundle.get('results'): continue
        event=events[0]; date=event['effective_date']
        corrected=bundle.get('supersedes_initial_history') or event['execution_status']=='INITIAL_HISTORY_RECONSTRUCTION'
        if corrected: rows={}  # Earlier defective observations remain archived, not forward returns.
        kind=('Corrected starting point' if corrected else 'Reconstructed missed session'
              if event.get('recovery_reconstruction') else 'Imported observation'
              if bundle.get('legacy_import') else 'Forward paper observation')
        nav=round(sum(r['state']['history'][-1][1] for r in bundle['results']),2)
        rows[date]={'Date':date,'Paper NAV':nav,
                    'Paper NAV + assumed income':round(nav+sum(scenario_net(r['state']) for r in bundle['results']),2),
                    'Nifty level':event.get('benchmark_level'),
                    'NIFTYBEES price':event.get('total_return_benchmark_level'),
                    'NIFTYBEES source':'captured at evaluation' if event.get('total_return_benchmark_level') else None,
                    'Record type':kind,'Recorded at':event['generated_at']}
    result=[rows[d] for d in sorted(rows)]
    closes=None
    for row in result:
        if row['NIFTYBEES price'] is None:
            closes=closes if closes is not None else _cached_closes(root,tr_symbol)
            row['NIFTYBEES price']=closes.get(row['Date'])
            row['NIFTYBEES source']='later vendor history' if row['NIFTYBEES price'] else 'unavailable'
    if result:
        first=result[0]
        for row in result:
            row['Paper index']=100*row['Paper NAV']/first['Paper NAV']
            row['Paper index + assumed income']=100*row['Paper NAV + assumed income']/first['Paper NAV']
            row['NIFTYBEES total-return index']=(100*row['NIFTYBEES price']/first['NIFTYBEES price']
                if row['NIFTYBEES price'] and first['NIFTYBEES price'] else None)
            row['Nifty price index']=100*row['Nifty level']/first['Nifty level'] if row['Nifty level'] and first['Nifty level'] else None
    return result


def success_status(rows, criteria):
    """Apply the pre-registered test to forward rows; recorded NAV only."""
    from datetime import date
    usable=[r for r in rows if r.get('NIFTYBEES total-return index')]
    if len(usable)<2:
        return {'verdict':'INCONCLUSIVE','reason':'Not enough forward observations with a benchmark.','years':0.}
    first,last=usable[0],usable[-1]
    years=(date.fromisoformat(last['Date'])-date.fromisoformat(first['Date'])).days/365.25
    paper=last['Paper index']/100; bench=last['NIFTYBEES total-return index']/100
    peak=0.; worst=0.
    for r in usable:
        peak=max(peak,r['Paper index']); worst=min(worst,r['Paper index']/peak-1)
    out={'years':years,'paper_return_pct':(paper-1)*100,'benchmark_return_pct':(bench-1)*100,
         'worst_drawdown_pct':worst*100,'start':first['Date'],'through':last['Date']}
    out['shortfall_pct']=out['benchmark_return_pct']-out['paper_return_pct']
    if years>=1:
        out['paper_cagr_pct']=(paper**(1/years)-1)*100; out['benchmark_cagr_pct']=(bench**(1/years)-1)*100
        out['excess_cagr_pct']=out['paper_cagr_pct']-out['benchmark_cagr_pct']
    if -worst*100>criteria['max_drawdown_limit_pct']:
        return dict(out,verdict='FAIL',reason='Worst drawdown breached the limit.')
    if years>=criteria['early_fail_after_years'] and out['shortfall_pct']>=criteria['early_fail_cumulative_shortfall_pct']:
        return dict(out,verdict='FAIL',reason='Cumulative return trails NIFTYBEES by the early-fail shortfall.')
    if years>=criteria['earliest_verdict_years']:
        if out['excess_cagr_pct']>=criteria['pass_min_excess_cagr_pct']:
            return dict(out,verdict='PASS',reason='Beat NIFTYBEES by the required margin within the drawdown limit.')
        if years>=criteria['final_verdict_years']:
            return dict(out,verdict='FAIL',reason='Final verdict reached without the required margin.')
    return dict(out,verdict='INCONCLUSIVE',reason=f"Too early: verdict possible after {criteria['earliest_verdict_years']} years.")


def portfolio_rows(books):
    holdings=[]; orders=[]
    for book in books:
        state=book['state']
        for symbol,h in state['holdings'].items():
            price=book.get('prices',{}).get(symbol)
            holdings.append({'Book':book['name'],'Symbol':symbol,'Units':h['qty'],
                             'Recorded price (INR)':price,
                             'Market value (INR)':round(h['qty']*price,2) if price is not None else None,
                             'Cost basis (INR)':h['cost'],'Stop (INR)':h.get('stop',0)})
        for order in state['orders']:
            orders.append({'Book':book['name'],'ID':order['id'],'Side':order['side'],
                           'Symbol':order['symbol'],'Status':order['status'],
                           'Decision date':order.get('decided_date'), 'Fill date':order.get('fill_date'),
                           'Units':order.get('qty'),'Fill price':order.get('fill_price'),
                           'Reason':order.get('reason') or order.get('pending_reason','')})
    return holdings,orders
