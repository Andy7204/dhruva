"""Read-only views of saved paper evidence; never recalculate signals or NAV."""
import json
from pathlib import Path


def forward_rows(root):
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
        rows[date]={'Date':date,'Paper NAV':round(sum(r['state']['history'][-1][1] for r in bundle['results']),2),
                    'Nifty level':event.get('benchmark_level'),'Record type':kind,
                    'Recorded at':event['generated_at']}
    result=[rows[d] for d in sorted(rows)]
    if result:
        nav=result[0]['Paper NAV']; benchmark=result[0]['Nifty level']
        for row in result:
            row['Paper index']=100*row['Paper NAV']/nav
            row['Nifty price index']=100*row['Nifty level']/benchmark if row['Nifty level'] and benchmark else None
    return result


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
