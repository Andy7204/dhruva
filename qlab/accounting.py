"""Fail-closed reconciliation invariants for repaired paper books."""
import math
from qlab import livebook, tax


def verify(results,cfg):
    if not results: raise ValueError('No books to reconcile')
    inventory=results[0]['state'].get('account_tax_inventory',{})
    quantities={};sales=[];reserve=0.
    for result in results:
        st=result['state'];sales.extend(st.get('realized_sales',[]))
        if st.get('account_tax_inventory',{})!=inventory:
            raise ValueError('Shared FIFO inventory mismatch')
        for key in ('cash','tax_reserve','charges_total'):
            value=st.get(key,0.)
            if not math.isfinite(value) or value<0: raise ValueError('Invalid accounting '+key)
        reserve+=st.get('tax_reserve',0.)
        orders=st['orders'];ids=[o['id'] for o in orders]
        if len(set(ids))!=len(ids): raise ValueError('Duplicate order identity')
        for receipt in st.get('receivables',[]):
            if not math.isfinite(receipt['amount']) or receipt['amount']<0:
                raise ValueError('Invalid settlement receivable')
        for symbol,h in st['holdings'].items():
            if h['qty']<=0 or int(h['qty'])!=h['qty'] or sum(l['qty'] for l in h['lots'])!=h['qty']:
                raise ValueError('FIFO quantity mismatch: '+symbol)
            if abs(sum(l['economic_cost'] for l in h['lots'])-h['cost'])>.011:
                raise ValueError('FIFO cost mismatch: '+symbol)
            quantities[symbol]=quantities.get(symbol,0)+h['qty']
        value=livebook.total_value(st,result['prices_now'])
        if abs(value-st['history'][-1][1])>.011: raise ValueError('Saved NAV mismatch')
    if quantities!={s:h['qty'] for s,h in inventory.items()}:
        raise ValueError('Aggregate holdings differ from shared FIFO')
    actual,_=tax.accrued_tax(sales,cfg)
    if abs(reserve-actual)>.011: raise ValueError('Shared tax reserve mismatch')
    return {'status':'PASS','tax_reserve':round(reserve,2),
            'nav':round(sum(r['state']['history'][-1][1] for r in results),2),
            'scope':'FIFO, cash, settlement receivables, order identities, shared tax and saved NAV'}
