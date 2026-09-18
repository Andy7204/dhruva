import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from dhruva.evidence import record_evaluation
from dhruva.ledger import Ledger


class EvidenceTests(unittest.TestCase):
    def test_two_books_snapshot_import_and_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            date = pd.Timestamp('2026-09-17')
            raw = {'TEST': pd.DataFrame({'adjclose': [100.0], 'open': [99.]}, index=[date])}
            panel = {'TEST': raw['TEST'].assign(mom_score=2., vol20=.3)}
            books = [{'name': b, 'capital': c, 'prices_now': {'TEST': 100.},
                      'state': {'name': b, 'as_of': '2026-09-17', 'capital': c,
                                'history': [['2026-09-17', c]], 'holdings': {}, 'orders': [], 'cash': c}}
                     for b, c in [('balanced', 70000), ('aggressive', 30000)]]
            previous = {b['name']: copy.deepcopy(b['state']) for b in books}
            with patch('dhruva.evidence.subprocess.check_output', return_value='testgit'):
                result, added = record_evaluation(root, {}, raw, raw['TEST'], panel, books, previous,
                                                  generated_at='2026-09-18T05:00:00+00:00')
                self.assertTrue(added)
                self.assertEqual(result, books)
                changed = copy.deepcopy(books)
                changed[0]['prices_now']['TEST'] = 900
                result, added = record_evaluation(root, {}, raw, raw['TEST'], panel, changed, previous)
                self.assertFalse(added)
                self.assertEqual(result, books)
            ledger = Ledger(root/'runs/ledger/dhruva_v1')
            self.assertEqual(ledger.verify()['events'], 2)
            record = ledger.find('dhruva-v1:2026-09-17')['payload']
            self.assertTrue(all(e['execution_status'] == 'IMPORTED_LEGACY_OBSERVATION' for e in record['events']))
            snapshot = ledger.read_snapshot(record['events'][0]['data_snapshot'])
            self.assertEqual(snapshot['market']['TEST']['rows'], [[100., 99.]])

    def test_new_scheduled_decision_has_required_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); date = pd.Timestamp('2026-09-17')
            raw = {'TEST': pd.DataFrame({'adjclose': [100.]}, index=[date])}
            books = [{'name': 'one', 'capital': 1000., 'prices_now': {'TEST': 100.},
                      'state': {'as_of': '2026-09-17', 'capital': 1000., 'holdings': {},
                                'history': [['2026-09-17', 1000.]], 'orders': [
                                    {'symbol': 'TEST', 'side': 'BUY', 'target_value': 100.,
                                     'decided_date': '2026-09-17', 'status': 'scheduled'}]}}]
            with patch('dhruva.evidence.subprocess.check_output', return_value='testgit'):
                record_evaluation(root, {}, raw, raw['TEST'], raw, books, {},
                                  generated_at='2026-09-18T05:00:00+00:00')
            e = Ledger(root/'runs/ledger/dhruva_v1').find('dhruva-v1:2026-09-17')['payload']['events'][0]
            self.assertEqual((e['action'], e['target_weight']), ('BUY', .1))
            self.assertEqual(e['execution_status'], 'SCHEDULED_NEXT_OPEN')
            self.assertEqual(e['generated_at'], '2026-09-18T05:00:00+00:00')


if __name__ == '__main__': unittest.main()
