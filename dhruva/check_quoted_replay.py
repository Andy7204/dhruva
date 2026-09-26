"""Read-only acceptance replay of captured Sep25 marks; never advances live files."""
import copy
import json
from pathlib import Path
import subprocess
import pandas as pd
from dhruva.ledger import Ledger, utc_now, digest
from dhruva.reconcile import frame
from qlab import livebook, indicators, engine, tax, accounting
from qlab.optimize import _apply


def check(root=None):
    root=Path(root or Path(__file__).resolve().parents[1])
    ledger=Ledger(root/'runs/ledger/dhruva_v1')
    verified=ledger.verify()
    previous=ledger.latest_for_date('2026-09-24')['payload']['state']
    captured=ledger.latest_for_date('2026-09-25')['payload']['state']
    snapshot=ledger.read_snapshot(captured['data_snapshot'])
    cfg=captured['config'];day=pd.Timestamp('2026-09-25')
    states={r['name']:copy.deepcopy(r['state']) for r in previous['results']}
    # This session has no rebalance: isolate the actual changed execution/mark
    # convention without claiming this is a full historical strategy rerun.
    assert all(st['step_count']%cfg['rebalance']['long_term_rerank_days']!=0 and
               not st.get('breaker') for st in states.values())
    symbols={s for st in states.values() for s in st['holdings']}
    panel={s:indicators.enrich(frame(snapshot['market'][s])) for s in symbols}
    benchmark=indicators.enrich(frame(snapshot['benchmark']))
    inventory=copy.deepcopy(next(iter(states.values()))['account_tax_inventory'])
    projections={p.name:digest(json.loads(p.read_text(encoding='utf-8'))) for p in (root/'runs').glob('livebook_*.json')}
    def sync(): tax.reserve_accounts(states,cfg)
    results=[]
    for name,bk in cfg['books'].items():
        cb=_apply(cfg,bk.get('overrides',{}));cb['starting_capital']=bk['capital']
        livebook.step(states[name],panel,day,cb,bool(engine.regime_series(cb,benchmark).loc[day]),
                      float(engine.regime_factor_series(cb,benchmark).loc[day]),sync,inventory)
        results.append({'name':name,'state':states[name],'prices_now':livebook.execution_prices(panel,day)})
    sync()
    for r in results:
        r['state']['account_tax_inventory']=copy.deepcopy(inventory)
        r['state']['history'][-1][1]=round(livebook.total_value(r['state'],r['prices_now']),2)
    result=accounting.verify(results,cfg)
    expected=sum(r['state']['history'][-1][1] for r in captured['results'])
    assert abs(result['nav']-expected)<.011
    repeated=copy.deepcopy(states)
    for name,st in states.items(): livebook.step(st,panel,day,cfg,False,1.)
    assert states==repeated
    assert projections=={p.name:digest(json.loads(p.read_text(encoding='utf-8'))) for p in (root/'runs').glob('livebook_*.json')}
    return {'generated_at':utc_now(),'producing_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'scope':'Read-only captured Sep25 no-rebalance execution/mark replay, not a new live run',
            'source_snapshot':captured['data_snapshot'],'ledger':verified,'accounting':result,
            'recorded_nav':expected,'duplicate_noop':True,'live_projections_unchanged':True}


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
