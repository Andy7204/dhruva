"""Apply evidenced cash/IDCW receipts to actual-unit paper books.

This reducer does not infer entitlements, allotment dates or TDS from yields.
Callers supply reconciled receipts. Historical receipts require an explicit
ledger correction; the normal daily path never silently rewrites old NAV.
"""
import copy
import math
import hashlib
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urlparse
from qlab import lots


def verify_source(root, receipt):
    """Daily ingestion accepts only a preserved local source with matching bytes."""
    root=Path(root).resolve()
    path=(root/receipt['source_path']).resolve()
    if not path.is_relative_to(root): raise ValueError('Income source outside project')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['source_sha256']:
        raise ValueError('Income source hash mismatch')


def post_receipt(state, inventory, receipt, as_of, previous_as_of=None):
    required={'id','book','symbol','gross','withheld','taxable_date','effective_date',
              'source_url','source_sha256','retrieved_at','mode'}
    if not required<=receipt.keys(): raise ValueError('Incomplete income receipt provenance')
    if receipt['book']!=state['name']: raise ValueError('Income receipt book mismatch')
    if state.get('price_convention')!='actual_quoted_units':
        raise ValueError('Income requires reconciled actual quoted units')
    if urlparse(receipt['source_url']).scheme!='https': raise ValueError('Income source must be HTTPS')
    sha=receipt['source_sha256']
    if len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
        raise ValueError('Invalid income source hash')
    observed=datetime.fromisoformat(receipt['retrieved_at'])
    if observed.tzinfo is None: raise ValueError('Income retrieval time must include timezone')
    effective=date.fromisoformat(receipt['effective_date'])
    taxable=date.fromisoformat(receipt['taxable_date'])
    day=date.fromisoformat(str(as_of))
    if effective>day: return False
    if taxable>day: raise ValueError('Income taxable date is in the future')
    if observed.date()>day: raise ValueError('Income source was retrieved after the evaluation date')
    prior=next((r for r in state.get('income_receipts',[]) if r['id']==receipt['id']),None)
    if prior:
        if prior!=receipt: raise ValueError('Income receipt identity changed')
        return False
    cutoff=date.fromisoformat(previous_as_of) if previous_as_of else day
    if effective<day and effective<=cutoff:
        raise ValueError('Late income receipt requires explicit ledger correction')
    for key in ('gross','withheld'):
        if not math.isfinite(receipt[key]) or receipt[key]<0: raise ValueError('Invalid income amount')
    gross=receipt['gross']; withheld=receipt['withheld'];net=gross-withheld
    if net<0: raise ValueError('TDS exceeds gross income')
    updated=copy.deepcopy(state); shared=copy.deepcopy(inventory)
    if receipt['mode']=='cash':
        updated['cash']=round(updated['cash']+net,2)
    elif receipt['mode']=='reinvested_units':
        qty=receipt['units'];price=receipt['unit_price'];residual=receipt.get('residual_cash',0.)
        if (not all(math.isfinite(v) for v in (qty,price,residual)) or qty<=0 or price<=0 or
                residual<0 or not math.isclose(qty*1000,round(qty*1000),rel_tol=0,abs_tol=1e-8)):
            raise ValueError('Invalid allotted distribution units')
        basis=round(qty*price,2)
        if abs(basis+residual-net)>.011: raise ValueError('Allotment/net income reconciliation failed')
        symbol=receipt['symbol'];identity=state['name']+':income:'+receipt['id']
        own=updated['holdings'].setdefault(symbol,{'kind':'cushion','stop':0.,'settle_date':str(day)})
        for holding in (own,shared.setdefault(symbol,{})):
            lots.buy(holding,qty,basis,{'total':0.,'stt':0.},str(effective),identity)
            next(lot for lot in holding['lots'] if lot['id']==identity)['origin']='distribution'
        updated['cash']=round(updated['cash']+residual,2)
    else: raise ValueError('Unsupported income receipt mode')
    updated['tax_prepaid']=round(updated.get('tax_prepaid',0.)+withheld,2)
    updated.setdefault('income_receipts',[]).append(copy.deepcopy(receipt))
    state.clear();state.update(updated)
    inventory.clear();inventory.update(shared)
    return True
