"""Explicit initial-paper-history correction using preserved orders and snapshots.

No network, no current-day run, no fabricated original generation timestamps.
Use --apply only after reviewing the dry-run reconciliation report.
"""
import copy
import gzip
import json
from pathlib import Path
import subprocess
import pandas as pd
from dhruva.ledger import Ledger, canonical, digest, utc_now, atomic_write, writer_lock
from qlab import livebook as L, tax, indicators
from qlab.optimize import _apply

ROOT=Path(__file__).resolve().parents[1]
KEY='initial-accounting-correction-2026-09-25'


def frame(obj):
    return pd.DataFrame(obj['rows'],index=pd.to_datetime(obj['dates']),columns=obj['columns'])


def build(root=ROOT):
    root=Path(root);ledger=Ledger(root/'runs/ledger/dhruva_v1');ledger.verify()
    segments=[json.loads(p.read_bytes()) for p in sorted((ledger.root/'segments').glob('*.json'))]
    original=[s for s in segments if s['payload']['idempotency_key'].startswith('dhruva-v1:')]
    if not original: raise ValueError('Original captured evidence required')
    cfg=json.loads((root/'config.json').read_text(encoding='utf-8'))
    first=original[0]['payload']['state'];latest=original[-1]['payload']['state']
    if latest['results'][0]['state']['as_of']!='2026-09-24':
        raise ValueError('This bounded repair only covers initial history through September24')
    seeds=first['previous'];states={};configs={}
    for name,bk in cfg['books'].items():
        cb=_apply(cfg,bk.get('overrides',{}));cb['starting_capital']=bk['capital']
        cb['excluded_momentum_assets']=list(cfg.get('defensive_basket',{}));configs[name]=cb
        st=L.new_livebook(cb,name)
        st.update(as_of='2026-09-16',inception='2026-09-16',step_count=1,
                  history=[['2026-09-16',bk['capital']]],processed_through='2026-09-16')
        for number,order in enumerate(seeds[name]['orders'],1):
            if order.get('decided_date')!='2026-09-16' or order['side']!='BUY':
                raise ValueError('Unexpected legacy seed order; inspect manually')
            o={k:copy.deepcopy(order[k]) for k in ('side','symbol','kind','decided_date','target_value','stop','ref_price')}
            o.update(id=f'{name}:legacy:{number}',legacy_id=order['id'],status='scheduled',
                     provenance='RECONSTRUCTED_FROM_ORIGINAL_INTENT')
            if o['ref_price']<=0:
                o.update(status='cancelled',cancelled_date='2026-09-16',
                         reason='Reconstruction: invalid original reference price; no executable intent')
            st['orders'].append(o)
        states[name]=st
    snapshots=[];prices={};dates=[];tax_inventory={}
    for i,segment in enumerate(original):
        bundle=segment['payload']['state'];sid=bundle['data_snapshot'];snapshots.append(sid)
        raw=json.loads(gzip.decompress((ledger.root/'snapshots'/f'{sid}.json.gz').read_bytes()))
        symbols={o['symbol'] for st in states.values() for o in st['orders'] if o['status']!='cancelled'}
        panel={s:indicators.enrich(frame(raw['market'][s])) for s in symbols}
        as_of=bundle['results'][0]['state']['as_of']
        days=['2026-09-17',as_of] if i==0 else [as_of]
        for day in days:
            date=pd.Timestamp(day)
            for name,st in states.items():
                old=seeds[name] if day=='2026-09-17' else next(r['state'] for r in bundle['results'] if r['name']==name)
                L.step(st,panel,date,configs[name],old.get('risk_on',False),1.,
                       tax_sync=lambda:tax.reserve_accounts(states,cfg),tax_inventory=tax_inventory)
                st['processed_through']=day
            tax.reserve_accounts(states,cfg)
            prices={s:float(p.at[date,'adjclose']) for s,p in panel.items()}
            for st in states.values(): st['history'][-1][1]=round(L.total_value(st,prices),2)
            dates.append(day)
    results=[];comparison={}
    for name,st in states.items():
        old=next(r['state'] for r in latest['results'] if r['name']==name)
        st.update(accounting_schema=2,history_quality='RECONSTRUCTED_INITIAL_PAPER_HISTORY',
                  account_tax_inventory=copy.deepcopy(tax_inventory),
                  reconstruction={'through':'2026-09-24','source_snapshots':snapshots,
                    'note':'Original intents, repaired accounting and captured daily bars; not original live signals'})
        results.append({'name':name,'state':st,'capital':st['capital'],'prices_now':prices})
        comparison[name]={'original_history':old['history'],'corrected_history':st['history'],
            'original_charges':old['charges_total'],'corrected_charges':st['charges_total'],
            'original_holdings':{s:h['qty'] for s,h in old['holdings'].items()},
            'corrected_holdings':{s:h['qty'] for s,h in st['holdings'].items()}}
    from qlab.accounting import verify
    verification=verify(results,cfg)
    return {'results':results,'verification':verification,'previous':{r['name']:r['state'] for r in latest['results']},
            'config':cfg,'source_snapshots':snapshots,'comparison':comparison,
            'supersedes_initial_history':True},original[-1]


def run(apply=False,root=ROOT):
    root=Path(root); ledger=Ledger(root/'runs/ledger/dhruva_v1')
    prior=ledger.find(KEY)
    if prior:
        if apply:
            latest=sorted((ledger.root/'segments').glob('*.json'))[-1]
            if json.loads(latest.read_bytes())['payload']['idempotency_key']!=KEY:
                raise ValueError('Later forward evidence exists; cannot republish an old correction')
            from qlab.orchestrator import _save_book
            for r in prior['payload']['state']['results']: _save_book(r['name'],r['state'],runs=root/'runs')
        return {'status':'ALREADY_RECORDED','head':prior['hash']}
    bundle,original=build(root)
    report={'observed_at':utc_now(),'applied':False,'comparison':bundle['comparison'],'verification':bundle['verification']}
    if apply:
        if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():
            raise ValueError('Commit producing repair code before applying correction')
        from qlab.orchestrator import _save_book
        with writer_lock(root/'runs/pipeline'):
            generated=utc_now();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            sid=ledger.snapshot({'captured_at':generated,'repair_config':bundle['config'],
                'source_snapshots':bundle['source_snapshots'],'comparison':bundle['comparison']})
            bundle['data_snapshot']=sid;events=[]
            for r in bundle['results']:
                old=next(e for e in original['payload']['events'] if e['strategy_id'].endswith(':'+r['name']))
                event=copy.deepcopy(old);event.pop('event_id')
                event.update(run_id=KEY,generated_at=generated,action='CORRECTION',
                    corrects_event_id=old['event_id'],git_commit=commit,configuration_hash=digest(bundle['config']),
                    data_snapshot=sid,ticker=None,company_name=None,signal_score=None,signal_components={},
                    previous_weight=None,target_weight=None,market_price=None,
                    portfolio_nav=r['state']['history'][-1][1],execution_status='INITIAL_HISTORY_RECONSTRUCTION',
                    rationale='Recalculate initial paper history with FIFO, costs, settled cash and shared reserve; preserve original evidence',
                    accounting_quality='REPAIRED_CORE_ADJUSTED_PRICE_RESEARCH_LIMITATIONS')
                events.append(event)
            envelope,_=ledger.append(KEY,events,bundle)
            for r in bundle['results']: _save_book(r['name'],r['state'],runs=root/'runs')
            report.update(applied=True,ledger_head=envelope['hash'],producing_commit=commit)
            atomic_write(root/'runs/reconciliation/initial_accounting.json',canonical(report)+b'\n')
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true')
    print(json.dumps(run(parser.parse_args().apply),indent=2))
