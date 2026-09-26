import copy
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class StreamlitTests(unittest.TestCase):
    def test_real_app_has_one_total_and_no_false_green(self):
        app = AppTest.from_file(str(ROOT/'streamlit_app.py')).run(timeout=60)
        self.assertEqual(len(app.exception), 0, list(app.exception))
        totals = [m for m in app.metric if m.label.startswith('Recorded value ')]
        self.assertEqual(len(totals), 1)
        books=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'runs').glob('livebook_*.json')]
        expected=sum(b['history'][-1][1] for b in books)
        self.assertEqual(totals[0].value,f'₹{expected:,.2f}')
        if all(b.get('accounting_schema')==2 for b in books):
            self.assertIn('after modeled tax reserve',totals[0].label)
        self.assertTrue(len(app.warning) or len(app.error))

    def test_corrupt_stale_and_failed_states_render_warnings(self):
        health = dict(status='UNHEALTHY', problems=['PORTFOLIO UNAVAILABLE: corrupt fixture',
                       'MARKET DATA STALE: fixture', 'BACKEND FAILED: fixture'], warnings=[],
                      last_success=None, last_attempt=None, market_date='2020-01-01',
                      expected_date='2026-09-17', portfolio_date=None, strategy_version='1.0',
                      git_commit='fixture', total=None, books=[])
        with patch('dhruva.health.inspect', return_value=health):
            app = AppTest.from_file(str(ROOT/'streamlit_app.py')).run(timeout=20)
        self.assertEqual(len(app.exception), 0, list(app.exception))
        errors = '\n'.join(e.value for e in app.error)
        for word in ('STALE', 'FAILED', 'withheld'): self.assertIn(word, errors)
        self.assertEqual(len(app.metric), 0)


if __name__ == '__main__': unittest.main()
