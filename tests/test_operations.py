from datetime import datetime
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dhruva.calendar import IST, expected_date, run_due, is_session
from dhruva import operations


class OperationsTests(unittest.TestCase):
    def test_stage_failure_is_durable_and_not_no_signal(self):
        import copy
        observed=[]
        def failed_pipeline(refresh, progress):
            progress('data_ingestion','COMPLETE')
            progress('data_validation','RUNNING')
            raise ValueError('fixture stale benchmark')
        with patch('dhruva.operations.write_attempt',side_effect=lambda r:observed.append(copy.deepcopy(r))):
            with patch('dhruva.operations.subprocess.check_output',return_value='fixture'), patch('dhruva.operations.run_due',return_value=(True,'DUE')):
                with patch('qlab.orchestrator.daily_run',side_effect=failed_pipeline):
                    with self.assertRaisesRegex(ValueError,'stale benchmark'): operations.run()
        last=observed[-1]
        self.assertEqual(last['status'],'FAILED')
        self.assertEqual(last['stages']['data_validation']['status'],'FAILED')
        self.assertEqual(last['stages']['portfolio_engine']['status'],'NOT_RUN')
        self.assertFalse(last['execution_completed'])

    def test_intraday_weekend_holiday_and_calendar_expiry(self):
        def dt(s): return datetime.fromisoformat(s).replace(tzinfo=IST)
        self.assertEqual(run_due(dt('2026-09-18T11:00'))[0], False)
        self.assertEqual(expected_date(dt('2026-09-18T11:00')), '2026-09-17')
        self.assertTrue(run_due(dt('2026-09-18T18:30'))[0])
        self.assertEqual(run_due(dt('2026-09-19T18:30'))[1], 'NON_TRADING_DAY')
        self.assertEqual(run_due(dt('2026-10-02T18:30'))[1], 'NON_TRADING_DAY')
        with self.assertRaises(ValueError): run_due(dt('2027-01-02T18:30'))

    def test_failure_record_written_and_exception_not_swallowed(self):
        observed = []
        with patch('dhruva.operations.write_attempt', side_effect=lambda r: observed.append(dict(r))):
            with patch('dhruva.operations.subprocess.check_output', return_value='fixture'):
                with patch('dhruva.operations.run_due', return_value=(True, 'DUE')):
                    with patch('qlab.orchestrator.daily_run', side_effect=RuntimeError('test API unavailable')):
                        with self.assertRaisesRegex(RuntimeError, 'test API unavailable'): operations.run()
        self.assertEqual(observed[0]['status'], 'RUNNING')
        self.assertEqual(observed[-1]['status'], 'FAILED')
        self.assertEqual(observed[-1]['errors'], ['RuntimeError: test API unavailable'])

    def test_intraday_never_calls_trading_pipeline(self):
        with patch('dhruva.operations.write_attempt'), patch('dhruva.operations.subprocess.check_output', return_value='fixture'):
            with patch('dhruva.operations.run_due', return_value=(False, 'BEFORE_COMPLETED_SESSION')):
                with patch('qlab.orchestrator.daily_run') as engine:
                    self.assertEqual(operations.run()['status'], 'SKIPPED_NOT_DUE')
                    engine.assert_not_called()


if __name__ == '__main__': unittest.main()
