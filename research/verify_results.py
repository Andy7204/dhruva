"""Independent cash-flow reconciliation and reproducibility record."""
import hashlib
import json
import subprocess
import sys

import pandas as pd
from challenge import ROOT, OUT, clean, D, E


def main():
    tests=subprocess.run([sys.executable,str(ROOT/'research/test_challenge.py')],capture_output=True,text=True)
    (OUT/'tests.txt').write_text(tests.stdout+tests.stderr)
    assert tests.returncode==0,tests.stderr
    results=json.loads((OUT/'results.json').read_text())
    reconciled={}
    for key,summary in results['full'].items():
        if not key.startswith('500/'):
            continue
        name=key.split('/')[1]
        ledger=pd.read_csv(OUT/f'trades_{name}.csv')
        delta=(ledger.qty*ledger.price*ledger.side.map({'buy':-1,'sell':1})-ledger.fee).sum()
        nav=100000+delta-summary['tax_rupees']
        # Tax in summary is rounded to paise; fill-ledger prices retain precision.
        assert abs(nav-summary['liquidation_nav'])<.02,(name,nav,summary)
        positions=(ledger.qty*ledger.side.map({'buy':1,'sell':-1})).groupby(ledger.s).sum()
        assert (positions==0).all(),positions
        reconciled[name]=round(nav,2)
    cfg=D.load_config(); prefix=[]
    for sym in ['RELIANCE.NS','HDFCBANK.NS','TCS.NS','GOLDBEES.NS', 'NIFTYBEES.NS']:
        p=ROOT/'data/cache'/(D._safe_name(sym)+'.csv')
        raw=clean(pd.read_csv(p,index_col='date',parse_dates=['date']))
        cut=raw.index[600]
        full=E.build_panel({sym:raw},cfg)[sym].loc[:cut]
        truncated=E.build_panel({sym:raw.loc[:cut]},cfg)[sym]
        pd.testing.assert_frame_equal(full,truncated)
        prefix.append(sym)
    manifest=json.loads((OUT/'manifest.json').read_text())
    assert manifest['protocol_sha256']==hashlib.sha256((ROOT/'research/PROTOCOL.md').read_bytes()).hexdigest()
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('qlab/','runs/','data/','.github/')) or p in ['config.json','streamlit_app.py','reports/dashboard.html'] for p in changed),changed
    sources=['research/challenge.py','research/scenarios.py','research/same_asset.py',
             'research/test_challenge.py','qlab/costs.py','qlab/tax.py','qlab/engine.py','qlab/indicators.py']
    out={'tests_passed':8,'cashflow_reconciled':reconciled,'actual_cache_prefix_invariance':prefix,
         'production_files_modified':False,'main_protocol_hash_matches':True,
         'sources_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}}
    (OUT/'verification.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))


if __name__=='__main__': main()
