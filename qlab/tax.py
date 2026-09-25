"""Shared-account capital-gains reserve; not a personal tax return.
Resident paper model: configured slab/surcharge, cess, FIFO taxable gains,
one exemption per FY, capital-loss setoff/carry assuming timely returns.
Current-period rates; external investments, basic allowance and rebate excluded.
"""
from collections import defaultdict
from datetime import date
import math


def _fy(value):
    d=date.fromisoformat(value)
    return d.year if d.month>=4 else d.year-1


def instrument_type(symbol,cfg):
    defaults={'GOLDBEES.NS':'listed_commodity_fund','SILVERBEES.NS':'listed_commodity_fund',
              'LIQUIDBEES.NS':'specified_debt_fund','INDIGRID.NS':'business_trust'}
    return cfg.get('instrument_types',{}).get(symbol,defaults.get(symbol,'listed_equity'))


def is_equity(symbol,cfg):
    return instrument_type(symbol,cfg) in ('listed_equity','equity_etf','business_trust')


def is_long(sale):
    if 'acquired' not in sale: return sale['holding_days']>365
    acquired=date.fromisoformat(sale['acquired'])
    try: anniversary=acquired.replace(year=acquired.year+1)
    except ValueError: anniversary=acquired.replace(year=acquired.year+1,day=28)
    return date.fromisoformat(sale['exit_date'])>anniversary


def accrued_tax(sales,cfg,income=()):
    tx=cfg.get('tax',{})
    if not tx.get('enabled'): return 0.,{}
    buckets=defaultdict(lambda:defaultdict(float))
    for sale in sales:
        if not math.isfinite(sale['gain']): raise ValueError('Nonfinite realized gain')
        kind=instrument_type(sale['symbol'],cfg)
        long=is_long(sale)
        if kind=='specified_debt_fund' and sale.get('acquired','2023-04-01')>='2023-04-01': long=False
        key=('eq_' if is_equity(sale['symbol'],cfg) else 'ne_')+('lt' if long else 'st')
        buckets[_fy(sale['exit_date'])][key]+=sale['gain']
    rates={'eq_st':tx['equity_stcg_pct'],'eq_lt':tx['equity_ltcg_pct'],
           'ne_st':tx['nonequity_short_pct'],'ne_lt':tx['nonequity_long_pct']}
    carry=[]; detail={};total=0.
    for year,bucket in sorted(buckets.items()):
        carry=[loss for loss in carry if year-loss['year']<=8]
        for term in ('lt','st'):
            amount=-sum(min(0,bucket.get(k,0)) for k in rates if k.endswith(term))
            if amount: carry.append({'year':year,'term':term,'amount':amount})
        gains={k:max(0,bucket.get(k,0)) for k in rates}
        # LT losses first, higher-rate eligible gains first. Exemption after setoff.
        for loss in sorted(carry,key=lambda x:(x['term']!='lt',x['year'])):
            eligible=[k for k in rates if loss['term']=='st' or k.endswith('lt')]
            for key in sorted(eligible,key=lambda k:(-rates[k],k)):
                offset=min(loss['amount'],gains[key]);gains[key]-=offset;loss['amount']-=offset
        gains['eq_lt']=max(0,gains['eq_lt']-tx['ltcg_exemption'])
        base=sum(gains[k]*rates[k] for k in rates)
        amount=round(base*(1+tx.get('surcharge_pct',0))*(1+tx.get('cess_pct',0.04)),2)
        detail[str(year)]={'tax':amount,'taxable_gains':gains,
            'loss_carry':{t:round(sum(x['amount'] for x in carry if x['term']==t),2) for t in ('st','lt')}}
        total+=amount
    # Cash dividends and reinvested IDCW are income, not capital gains. Capital
    # losses/exemption must never shelter this income. TDS is a prepaid-tax asset,
    # not a reduction of gross taxable income or of this gross liability.
    income_by_year=defaultdict(float)
    seen=set()
    for receipt in income:
        identity=(receipt['book'],receipt['id'])
        if identity in seen: raise ValueError('Duplicate income receipt')
        seen.add(identity)
        gross=receipt['gross']
        if not math.isfinite(gross) or gross<0: raise ValueError('Invalid gross income')
        income_by_year[_fy(receipt['taxable_date'])]+=gross
    slab=tx.get('income_slab_pct',tx.get('nonequity_short_pct',0.3))
    if not math.isfinite(slab) or not 0<=slab<=1: raise ValueError('Invalid income slab')
    for year,gross in income_by_year.items():
        amount=round(gross*slab*(1+tx.get('surcharge_pct',0))*(1+tx.get('cess_pct',0.04)),2)
        entry=detail.setdefault(str(year),{'tax':0.,'taxable_gains':{},'loss_carry':{}})
        entry.update(income_gross=round(gross,2),income_tax=amount)
        entry['tax']=round(entry['tax']+amount,2)
        total+=amount
    return round(total,2),detail


def reserve_accounts(states,cfg):
    """One taxpayer: prorate reserve by positive taxable gains, with exact cents.
    Attribution only, no cash transfer or duplicate exemptions. Gross cash stays
    recorded; available cash and NAV subtract reserve. Prior FY tax stays reserved.
    """
    sales=[s for state in states.values() for s in state.get('realized_sales',[])]
    income=[r for state in states.values() for r in state.get('income_receipts',[])]
    total,detail=accrued_tax(sales,cfg,income)
    weights={name:sum(max(0,s['gain']) for s in st.get('realized_sales',[]))+
             sum(r['gross'] for r in st.get('income_receipts',[])) for name,st in states.items()}
    denom=sum(weights.values());remaining=total
    names=sorted(states)
    for i,name in enumerate(names):
        amount=remaining if i==len(names)-1 else (round(total*weights[name]/denom,2) if denom else 0.)
        remaining=round(remaining-amount,2)
        states[name].update(tax_reserve=amount,tax_accrued=amount,tax_detail=detail,
                            account_tax_total=total,tax_scope='SHARED_PAPER_ACCOUNT')
    return total,detail
