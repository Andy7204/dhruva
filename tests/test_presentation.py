import json
from pathlib import Path
import tempfile
import unittest
from dhruva.presentation import forward_rows


class PresentationTests(unittest.TestCase):
    def test_correction_resets_baseline_and_recovery_stays_labelled(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); folder=root/'runs/ledger/dhruva_v1/segments';folder.mkdir(parents=True)
            for i,(date,nav,status,recovered) in enumerate([
                    ('2026-09-23',999,'EVALUATED',False),
                    ('2026-09-24',100,'INITIAL_HISTORY_RECONSTRUCTION',False),
                    ('2026-09-25',110,'EVALUATED',False),
                    ('2026-09-28',105,'EVALUATED',True)]):
                data={'payload':{'events':[{'effective_date':date,'execution_status':status,
                    'recovery_reconstruction':recovered,'benchmark_level':200+i,'generated_at':'actual-retrieval'}],
                    'state':{'results':[{'state':{'history':[[date,nav]]}}]}}}
                (folder/f'{i}.json').write_text(json.dumps(data))
            rows=forward_rows(root)
            self.assertEqual(len(rows),3)
            self.assertEqual(rows[0]['Paper index'],100)
            self.assertEqual(rows[1]['Paper index'],110)
            self.assertEqual(rows[2]['Record type'],'Reconstructed missed session')
            self.assertEqual(rows[0]['Record type'],'Corrected starting point')
