"""Prospective sensitivity estimate, never an entitlement or spendable receipt."""
from datetime import date
import math

MODEL = {'id':'liquidbees-scenario-2026-09-29', 'start':'2026-09-30',
         'symbol':'LIQUIDBEES.NS', 'annual_rate':0.04, 'unit_basis':1000.0}


def accrue(state, previous, as_of, tax_rate):
    """Simple ACT/365 on prior-close settled units, no reinvestment assumed.

    The prior close is the exposure proxy for every intervening calendar day.
    This deliberately does not claim exchange/AMC entitlement precision.
    """
    if not math.isfinite(tax_rate) or not 0<=tax_rate<=1:
        raise ValueError('Invalid income scenario tax rate')
    if not previous or not previous.get('as_of'): return
    day=date.fromisoformat(as_of)
    prior=date.fromisoformat(previous['as_of'])
    if day<=prior or day<date.fromisoformat(MODEL['start']): return
    existing=state.get('income_scenario')
    if existing and existing['as_of']>=as_of: return
    if existing and existing['model']!=MODEL: raise ValueError('Income scenario assumptions changed')
    start=max(prior,date.fromisoformat(MODEL['start']))
    days=max(0,(day-start).days)
    holding=previous.get('holdings',{}).get(MODEL['symbol'],{})
    qty=sum(lot['qty'] for lot in holding.get('lots',[])
            if lot.get('settle_date',holding.get('settle_date','9999-12-31'))<=previous['as_of'])
    gross=(existing or {}).get('gross',0.)+qty*MODEL['unit_basis']*MODEL['annual_rate']*days/365
    modeled_tax=(existing or {}).get('tax',0.)+qty*MODEL['unit_basis']*MODEL['annual_rate']*days/365*tax_rate
    state['income_scenario']={'model':dict(MODEL),'as_of':as_of,'gross':gross,
        'tax':modeled_tax,'net':gross-modeled_tax,'last_tax_rate':tax_rate,
        'status':'ASSUMPTION_ONLY_NOT_IN_NAV', 'days_added':days}


CASH_MODEL = {'id':'idle-cash-yield-2026-09-29', 'start':'2026-09-30',
              'annual_rate':0.04, 'basis':'prior-close settled cash'}


def accrue_cash(state, previous, as_of, tax_rate):
    """Assumed after-tax yield on idle settled cash, as if parked in a liquid fund.

    Same simple ACT/365 basis as the LIQUIDBEES scenario; kept outside NAV/cash.
    """
    if not math.isfinite(tax_rate) or not 0<=tax_rate<=1:
        raise ValueError('Invalid cash yield tax rate')
    if not previous or not previous.get('as_of'): return
    day=date.fromisoformat(as_of)
    prior=date.fromisoformat(previous['as_of'])
    if day<=prior or day<date.fromisoformat(CASH_MODEL['start']): return
    existing=state.get('cash_yield_scenario')
    if existing and existing['as_of']>=as_of: return
    if existing and existing['model']!=CASH_MODEL: raise ValueError('Cash yield assumptions changed')
    days=max(0,(day-max(prior,date.fromisoformat(CASH_MODEL['start']))).days)
    added=max(0.,previous.get('cash',0.))*CASH_MODEL['annual_rate']*days/365
    gross=(existing or {}).get('gross',0.)+added
    modeled_tax=(existing or {}).get('tax',0.)+added*tax_rate
    state['cash_yield_scenario']={'model':dict(CASH_MODEL),'as_of':as_of,'gross':gross,
        'tax':modeled_tax,'net':gross-modeled_tax,'last_tax_rate':tax_rate,
        'status':'ASSUMPTION_ONLY_NOT_IN_NAV','days_added':days}


def scenario_net(state):
    """Total assumed after-tax income (LIQUIDBEES + idle cash) for display only."""
    return sum((state.get(k) or {}).get('net',0.) for k in ('income_scenario','cash_yield_scenario'))
