from datetime import datetime
import unittest
from unittest.mock import patch
from dhruva.calendar import IST
from dhruva.watchdog import evaluate
from dhruva.watchdog import calendar_maintenance
from pathlib import Path
import tempfile
import json


class WatchdogTests(unittest.TestCase):
    def test_calendar_notice_boundary_both_calendars_and_expiry(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir()
            for name in ('trading_calendar.json','settlement_calendar.json'):
                (root/'data'/name).write_text(json.dumps({'valid_through':'2026-10-31'}))
            self.assertEqual(calendar_maintenance(root,datetime(2026,10,16,tzinfo=IST)),[])
            warnings=calendar_maintenance(root,datetime(2026,10,17,tzinfo=IST))
            self.assertEqual(len(warnings),2)
            self.assertTrue(all('14 days remaining' in w for w in warnings))
            self.assertTrue(all('-1 days remaining' in w for w in calendar_maintenance(root,datetime(2026,11,1,tzinfo=IST))))
            (root/'data/trading_calendar.json').write_text('{broken')
            self.assertTrue(any('CALENDAR UNREADABLE' in w for w in calendar_maintenance(root,datetime(2026,10,16,tzinfo=IST))))

    def test_advance_notice_enters_existing_external_alert_errors(self):
        with patch('dhruva.watchdog.inspect',return_value=self.health()),patch(
                'dhruva.watchdog.calendar_maintenance',return_value=['CALENDAR MAINTENANCE: fixture']):
            result=evaluate(now=datetime(2026,9,24,2,30,tzinfo=IST))
        self.assertEqual(result['status'],'FAILED')
        self.assertIn('CALENDAR MAINTENANCE: fixture',result['errors'])

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
