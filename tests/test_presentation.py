import json
from pathlib import Path
import tempfile
import unittest
from dhruva.presentation import forward_rows, success_status


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


CRITERIA={'earliest_verdict_years':3,'final_verdict_years':5,'pass_min_excess_cagr_pct':2.0,
          'max_drawdown_limit_pct':25.0,'early_fail_after_years':1,'early_fail_cumulative_shortfall_pct':15.0}


def rows(points):
    return [{'Date':d,'Paper index':p,'NIFTYBEES total-return index':b} for d,p,b in points]


class SuccessTests(unittest.TestCase):
    def test_total_return_benchmark_and_assumed_income_are_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); folder=root/'runs/ledger/dhruva_v1/segments';folder.mkdir(parents=True)
            (root/'data/cache').mkdir(parents=True)
            (root/'data/cache/NIFTYBEES_NS.csv').write_text('date,close\n2026-10-01,200\n')
            for i,(date,nav,tr) in enumerate([('2026-10-01',100,None),('2026-10-02',110,220)]):
                data={'payload':{'events':[{'effective_date':date,'execution_status':'EVALUATED',
                    'benchmark_level':100,'total_return_benchmark_level':tr,'generated_at':'t'}],
                    'state':{'results':[{'state':{'history':[[date,nav]],'cash_yield_scenario':{'net':5}}}]}}}
                (folder/f'{i}.json').write_text(json.dumps(data))
            out=forward_rows(root)
            self.assertEqual(out[0]['NIFTYBEES source'],'later vendor history')
            self.assertEqual(out[1]['NIFTYBEES total-return index'],110)
            self.assertEqual(out[1]['Paper index'],110)
            self.assertEqual(out[1]['Paper NAV + assumed income'],115)

    def test_verdicts(self):
        early=success_status(rows([('2026-10-01',100,100),('2027-06-01',130,100)]),CRITERIA)
        self.assertEqual(early['verdict'],'INCONCLUSIVE')
        crash=success_status(rows([('2026-10-01',100,100),('2026-11-01',74,90)]),CRITERIA)
        self.assertEqual(crash['verdict'],'FAIL')
        lagging=success_status(rows([('2026-10-01',100,100),('2027-10-10',100,116)]),CRITERIA)
        self.assertEqual(lagging['verdict'],'FAIL')
        passed=success_status(rows([('2026-10-01',100,100),('2029-10-02',140,120)]),CRITERIA)
        self.assertEqual(passed['verdict'],'PASS')
        final=success_status(rows([('2026-10-01',100,100),('2031-10-02',150,150)]),CRITERIA)
        self.assertEqual(final['verdict'],'FAIL')
