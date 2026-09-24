from datetime import datetime
import unittest
from unittest.mock import patch
from dhruva.calendar import IST
from dhruva.watchdog import evaluate


class WatchdogTests(unittest.TestCase):
    def health(self, date='2026-09-23'):
        return dict(problems=[],warnings=['Accounting pending'],market_date=date,
                    portfolio_date=date,last_success={'market_date':date,'run_id':'fixture'},
                    ledger={'events':10,'head':'fixture'})

    def test_current_evidence_passes_without_certifying_accounting(self):
        with patch('dhruva.watchdog.inspect',return_value=self.health()):
            result=evaluate(now=datetime(2026,9,24,2,30,tzinfo=IST))
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['warnings'],['Accounting pending'])

    def test_missed_run_detected_even_without_failure_record(self):
        with patch('dhruva.watchdog.inspect',return_value=self.health('2026-09-22')):
            result=evaluate(now=datetime(2026,9,24,2,30,tzinfo=IST))
        self.assertEqual(result['status'],'FAILED')
        self.assertTrue(any('MISSED_RUN' in e for e in result['errors']))

    def test_next_session_not_yet_due_and_missing_ledger(self):
        h=self.health(); h['problems']=['PORTFOLIO STALE: 2026-09-23; expected 2026-09-24']
        with patch('dhruva.watchdog.inspect',return_value=h):
            self.assertEqual(evaluate(now=datetime(2026,9,24,17,0,tzinfo=IST))['status'],'PASS')
            h['ledger']={}
            self.assertIn('LEDGER_HEARTBEAT_MISSING',evaluate(now=datetime(2026,9,24,17,0,tzinfo=IST))['errors'])


if __name__=='__main__': unittest.main()
