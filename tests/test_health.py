import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from dhruva.calendar import IST
from dhruva.health import inspect


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('config.json', {'books': {'balanced': {'capital': 70000}, 'aggressive': {'capital': 30000}}})
        for name, capital in [('balanced', 70000), ('aggressive', 30000)]:
            self.write(f'runs/livebook_{name}.json', {'capital': capital, 'as_of': '2026-09-17',
                                                    'history': [['2026-09-17', capital]]})
        (self.root/'data/cache').mkdir(parents=True)
        (self.root/'data/cache/_IDX_NSEI.csv').write_text('date,close\n2026-09-17,20000\n')
        self.write('runs/operations/latest.json', {'run_id': 'fixture', 'status': 'SKIPPED_NOT_DUE'})
        self.now = datetime(2026, 9, 18, 9, 0, tzinfo=IST)

    def write(self, path, data):
        p = self.root/path; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding='utf-8')

    def health(self, now=None):
        with patch('dhruva.health.verify_v1'), patch('dhruva.health.subprocess.check_output', return_value='fixture'):
            return inspect(self.root, now or self.now)

    def test_valid_v1_degraded_and_total_matches_books(self):
        h = self.health()
        self.assertEqual(h['status'], 'DEGRADED')
        self.assertEqual(h['total'], 100000)
        self.assertEqual(h['total'], sum(b['value'] for b in h['books']))

    def test_stale_after_completed_session(self):
        h = self.health(datetime(2026, 9, 18, 19, 0, tzinfo=IST))
        self.assertEqual(h['status'], 'UNHEALTHY')
        self.assertTrue(any('STALE' in p for p in h['problems']))

    def test_corrupt_book_withholds_all_totals(self):
        (self.root/'runs/livebook_aggressive.json').write_text('{broken')
        h = self.health()
        self.assertIsNone(h['total'])
        self.assertEqual(h['status'], 'UNHEALTHY')

    def test_failed_backend_never_healthy(self):
        self.write('runs/operations/latest.json', {'status': 'FAILED', 'errors': ['fixture']})
        h = self.health()
        self.assertEqual(h['status'], 'UNHEALTHY')
        self.assertTrue(any('BACKEND FAILED' in p for p in h['problems']))

    def test_intraday_date_rejected(self):
        (self.root/'data/cache/_IDX_NSEI.csv').write_text('date,close\n2026-09-18,20000\n')
        self.assertTrue(any('unfinished' in p for p in self.health()['problems']))

    def test_projection_differs_from_latest_ledger_is_unhealthy(self):
        self.write('runs/ledger/dhruva_v1/segments/fixture.json',
                   {'payload':{'state':{'results':[{'name':'balanced','state':{'changed':True}}]}}})
        with patch('dhruva.health.Ledger.verify',return_value={'events':1}):
            h=self.health()
        self.assertTrue(any('PORTFOLIO/LEDGER MISMATCH' in p for p in h['problems']))
        self.assertEqual(h['status'],'UNHEALTHY')


if __name__ == '__main__': unittest.main()
