"""Fail-closed reconciliation invariants for repaired paper books."""
import math
from qlab import livebook, tax


def _verify_inventory(inventory):
    for symbol, holding in inventory.items():
        lots=holding.get('lots',[])
        if not lots: raise ValueError('Missing FIFO lots: '+symbol)
        ids=[lot['id'] for lot in lots]
        if len(ids)!=len(set(ids)): raise ValueError('Duplicate FIFO lot: '+symbol)
        for lot in lots:
            qty=lot['qty']
            if not math.isfinite(qty) or qty<=0 or int(qty)!=qty:
                raise ValueError('Invalid FIFO quantity: '+symbol)
            for key in ('economic_cost','tax_cost'):
                if not math.isfinite(lot[key]) or lot[key]<0:
                    raise ValueError('Invalid FIFO basis: '+symbol)
        if sum(lot['qty'] for lot in lots)!=holding['qty']:
            raise ValueError('FIFO quantity mismatch: '+symbol)
        if not math.isfinite(holding['cost']) or abs(sum(lot['economic_cost'] for lot in lots)-holding['cost'])>.011:
            raise ValueError('FIFO cost mismatch: '+symbol)


def verify(results,cfg):
    if not results: raise ValueError('No books to reconcile')
    inventory=results[0]['state'].get('account_tax_inventory',{})
    _verify_inventory(inventory)
    quantities={};sales=[];reserve=0.;account_order_ids=set();book_names=set()
    for result in results:
        st=result['state'];sales.extend(st.get('realized_sales',[]))
        if st['name'] in book_names: raise ValueError('Duplicate book identity')
        book_names.add(st['name'])
        for sale in st.get('realized_sales',[]):
            if not math.isfinite(sale['gain']): raise ValueError('Nonfinite realized gain')
        if st.get('account_tax_inventory',{})!=inventory:
            raise ValueError('Shared FIFO inventory mismatch')
        for key in ('cash','tax_reserve','charges_total'):
            value=st.get(key,0.)
            if not math.isfinite(value) or value<0: raise ValueError('Invalid accounting '+key)
        reserve+=st.get('tax_reserve',0.)
        orders=st['orders'];ids=[o['id'] for o in orders]
        if len(set(ids))!=len(ids): raise ValueError('Duplicate order identity')
        if account_order_ids.intersection(ids): raise ValueError('Duplicate account order identity')
        account_order_ids.update(ids)
        for receipt in st.get('receivables',[]):
            if not math.isfinite(receipt['amount']) or receipt['amount']<0:
                raise ValueError('Invalid settlement receivable')
        _verify_inventory(st['holdings'])
        for symbol,h in st['holdings'].items():
            if h['qty']<=0 or int(h['qty'])!=h['qty'] or sum(l['qty'] for l in h['lots'])!=h['qty']:
                raise ValueError('FIFO quantity mismatch: '+symbol)
            if abs(sum(l['economic_cost'] for l in h['lots'])-h['cost'])>.011:
                raise ValueError('FIFO cost mismatch: '+symbol)
            quantities[symbol]=quantities.get(symbol,0)+h['qty']
        value=livebook.total_value(st,result['prices_now'])
        if not math.isfinite(value) or not math.isfinite(st['history'][-1][1]):
            raise ValueError('Nonfinite NAV')
        if abs(value-st['history'][-1][1])>.011: raise ValueError('Saved NAV mismatch')
    if quantities!={s:h['qty'] for s,h in inventory.items()}:
        raise ValueError('Aggregate holdings differ from shared FIFO')
    income=[receipt for r in results for receipt in r['state'].get('income_receipts',[])]
    actual,_=tax.accrued_tax(sales,cfg,income)
    if abs(reserve-actual)>.011: raise ValueError('Shared tax reserve mismatch')
    return {'status':'PASS','tax_reserve':round(reserve,2),
            'nav':round(sum(r['state']['history'][-1][1] for r in results),2),
            'scope':'FIFO, cash, settlement receivables, order identities, shared tax and saved NAV'}
