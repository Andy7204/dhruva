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
            # FIFO sales can leave a fractional remainder even in an originally
            # whole-unit buy lot, after consuming an older distribution lot.
            precision=1000
            if not math.isfinite(qty) or qty<=0 or not math.isclose(qty*precision,round(qty*precision),rel_tol=0,abs_tol=1e-8):
                raise ValueError('Invalid FIFO quantity: '+symbol)
            for key in ('economic_cost','tax_cost'):
                if not math.isfinite(lot[key]) or lot[key]<0:
                    raise ValueError('Invalid FIFO basis: '+symbol)
        if not math.isclose(sum(lot['qty'] for lot in lots),holding['qty'],rel_tol=0,abs_tol=1e-8):
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
        for key in ('cash','tax_reserve','charges_total','tax_prepaid'):
            value=st.get(key,0.)
            if not math.isfinite(value) or value<0: raise ValueError('Invalid accounting '+key)
        reserve+=st.get('tax_reserve',0.)
        receipts=st.get('income_receipts',[])
        if any(not math.isfinite(r.get('withheld',0.)) or not 0<=r.get('withheld',0.)<=r['gross'] for r in receipts):
            raise ValueError('Invalid receipt withholding')
        if any(r['book']!=st['name'] for r in receipts): raise ValueError('Income receipt attribution mismatch')
        if abs(st.get('tax_prepaid',0.)-sum(r.get('withheld',0.) for r in receipts))>.011:
            raise ValueError('Prepaid tax/receipt mismatch')
        orders=st['orders'];ids=[o['id'] for o in orders]
        if len(set(ids))!=len(ids): raise ValueError('Duplicate order identity')
        if account_order_ids.intersection(ids): raise ValueError('Duplicate account order identity')
        account_order_ids.update(ids)
        for receipt in st.get('receivables',[]):
            if not math.isfinite(receipt['amount']) or receipt['amount']<0:
                raise ValueError('Invalid settlement receivable')
        _verify_inventory(st['holdings'])
        for symbol,h in st['holdings'].items():
            if h['qty']<=0 or not math.isclose(sum(l['qty'] for l in h['lots']),h['qty'],rel_tol=0,abs_tol=1e-8):
                raise ValueError('FIFO quantity mismatch: '+symbol)
            if abs(sum(l['economic_cost'] for l in h['lots'])-h['cost'])>.011:
                raise ValueError('FIFO cost mismatch: '+symbol)
            quantities[symbol]=quantities.get(symbol,0)+h['qty']
        value=livebook.total_value(st,result['prices_now'])
        if not math.isfinite(value) or not math.isfinite(st['history'][-1][1]):
            raise ValueError('Nonfinite NAV')
        if abs(value-st['history'][-1][1])>.011: raise ValueError('Saved NAV mismatch')
    if set(quantities)!=set(inventory) or any(not math.isclose(quantities[s],inventory[s]['qty'],rel_tol=0,abs_tol=1e-8) for s in quantities):
        raise ValueError('Aggregate holdings differ from shared FIFO')
    income=[receipt for r in results for receipt in r['state'].get('income_receipts',[])]
    actual,_=tax.accrued_tax(sales,cfg,income)
    if abs(reserve-actual)>.011: raise ValueError('Shared tax reserve mismatch')
    return {'status':'PASS','tax_reserve':round(reserve,2),
            'nav':round(sum(r['state']['history'][-1][1] for r in results),2),
            'scope':'FIFO, cash, settlement receivables, order identities, shared tax and saved NAV'}
