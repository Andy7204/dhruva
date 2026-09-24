"""Verify fetched real deployment evidence; repeat capture only in a temporary copy.

Does not fetch quotes, run today's strategy, or change production state.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dhruva.evidence import record_evaluation
from dhruva.health import inspect
from dhruva.ledger import Ledger, utc_now


def main():
    health = inspect(ROOT)
    source = ROOT/'runs/ledger/dhruva_v1'
    ledger = Ledger(source)
    verified = health['ledger']
    date = health['portfolio_date']
    original = ledger.find('dhruva-v1:'+date)
    bundle = original['payload']['state']
    assert {r['name']: r['state'] for r in bundle['results']} == {
        b['name']: b['state'] for b in health['books']}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Same-day return resolves the existing segment without fetching or new input.
        shutil.copytree(source/'segments', root/'runs/ledger/dhruva_v1/segments')
        shutil.copy2(source/'checkpoint.json', root/'runs/ledger/dhruva_v1/checkpoint.json')
        changed = copy.deepcopy(bundle['results'])
        changed[0]['prices_now'] = {'MUTATED_TEST_QUOTE': 1.}
        for _ in range(2):
            results, added = record_evaluation(root, bundle['config'], {}, None, {},
                                               changed, bundle['previous'])
            assert not added and results == bundle['results']
        duplicate = Ledger(root/'runs/ledger/dhruva_v1').verify(verify_snapshots=False)
        assert duplicate == verified
    health.pop('books')
    evidence = dict(observed_at=utc_now(), source_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(), health=health,
        projection_matches_ledger=True, duplicate_capture_preserves_original=True,
        duplicate_scope='Two captures in temporary copy of real segments; not a new production daily run',
        production_ledger_unchanged=ledger.verify() == verified)
    path = ROOT/'docs/evidence/phase4_after_close.json'
    path.write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in evidence.items() if k != 'health'}, indent=2))


if __name__ == '__main__': main()
