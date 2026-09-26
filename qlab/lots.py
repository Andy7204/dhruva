"""FIFO inventory with separate economic and tax basis (STT is not deductible)."""
from datetime import date
import math


def buy(holding, qty, gross, charges, acquired, order_id):
    holding.setdefault('lots',[]).append({'id':order_id,'qty':qty,'acquired':acquired,
        'economic_cost':round(gross+charges['total'],2),
        'tax_cost':round(gross+charges['total']-charges['stt'],2)})
    holding['lots'].sort(key=lambda lot:lot['acquired'])
    summarize(holding)


def summarize(holding):
    holding['qty']=round(sum(l['qty'] for l in holding['lots']),9)
    holding['cost']=round(sum(l['economic_cost'] for l in holding['lots']),2)
    holding['avg']=holding['cost']/holding['qty'] if holding['qty'] else 0.
    if holding['lots']: holding['acquired']=holding['lots'][0]['acquired']


def sell(holding, qty, gross, charges, exited, symbol, order_id):
    if not holding.get('lots') or not math.isclose(sum(l['qty'] for l in holding['lots']),holding['qty'],rel_tol=0,abs_tol=1e-8):
        raise ValueError('FIFO lots missing/inconsistent; initial-history reconciliation required')
    if qty<=0 or qty>holding['qty']: raise ValueError('Invalid FIFO sale quantity')
    left=qty; records=[]
    for lot in holding['lots']:
        if not left: break
        used=min(left,lot['qty']); fraction=used/lot['qty']; share=used/qty
        economic=round(lot['economic_cost']*fraction,2)
        basis=round(lot['tax_cost']*fraction,2)
        records.append({'symbol':symbol,'order_id':order_id,'lot_id':lot['id'],
            'qty':used,'acquired':lot['acquired'],'exit_date':exited,
            'holding_days':(date.fromisoformat(exited)-date.fromisoformat(lot['acquired'])).days,
            'gain':round((gross-charges['total']+charges['stt'])*share-basis,2),
            'economic_gain':round((gross-charges['total'])*share-economic,2)})
        lot['qty']=round(lot['qty']-used,9);lot['economic_cost']=round(lot['economic_cost']-economic,2)
        lot['tax_cost']=round(lot['tax_cost']-basis,2);left-=used
    holding['lots']=[l for l in holding['lots'] if l['qty']]
    summarize(holding)
    return records
