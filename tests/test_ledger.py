import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dhruva.ledger import Ledger, LedgerError, ZERO


def event(**updates):
    value = dict(run_id='synthetic-acceptance', generated_at='2026-09-18T05:00:00+00:00',
                 data_cutoff_at='2026-09-17T10:00:00+00:00', effective_date='2026-09-17',
                 strategy_id='TEST_ONLY', strategy_version='test', git_commit='synthetic',
                 configuration_hash='synthetic', data_snapshot=None, ticker='TEST', company_name='Test fixture',
                 action='BUY', previous_weight=0, target_weight=0.1, signal_score=1,
                 signal_components={'fixture': True}, market_price=100, rationale='Synthetic acceptance only',
                 portfolio_nav=100000, benchmark_level=20000, execution_mode='PAPER',
                 execution_status='TEST_ONLY')
    value.update(updates)
    return value


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'ledger'
        self.ledger = Ledger(self.root)

    def test_restart_duplicate_and_conflict(self):
        original, added = self.ledger.append('test1', [event()], {'cash': 100})
        self.assertTrue(added)
        result = subprocess.run([sys.executable, '-B', '-c',
                                 'from dhruva.ledger import Ledger; import sys; print(Ledger(sys.argv[1]).verify())',
                                 str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(original['hash'], result.stdout)
        again, added = Ledger(self.root).append('test1', [event()], {'cash': 100})
        self.assertFalse(added)
        self.assertEqual(original, again)
        with self.assertRaises(LedgerError):
            self.ledger.append('test1', [event(target_weight=0.2)])

    def test_content_tamper_and_tail_deletion_detected(self):
        first, _ = self.ledger.append('one', [event()])
        second, _ = self.ledger.append('two', [event(action='HOLD')])
        paths = sorted((self.root/'segments').glob('*.json'))
        raw = paths[0].read_bytes()
        paths[0].write_bytes(raw.replace(b'100000', b'999999'))
        with self.assertRaises(LedgerError): self.ledger.verify()
        paths[0].write_bytes(raw)
        paths[1].unlink()
        with self.assertRaises(LedgerError): self.ledger.verify()

    def test_corrections_append_without_changing_original(self):
        original, _ = self.ledger.append('one', [event()])
        path = next((self.root/'segments').glob('*.json'))
        raw = path.read_bytes()
        correction = event(action='CORRECTION', corrects_event_id=original['payload']['events'][0]['event_id'])
        self.ledger.append('correction', [correction])
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(self.ledger.verify()['events'], 2)

    def test_latest_date_selects_correction_without_replacing_original(self):
        state={'results':[{'name':'fixture','state':{'as_of':'2026-09-17','cash':100}}]}
        original,_=self.ledger.append('dhruva-v1:2026-09-17',[event()],state)
        corrected=copy.deepcopy(state);corrected['results'][0]['state']['cash']=99
        newer,_=self.ledger.append('repair',[event(action='CORRECTION',corrects_event_id=original['payload']['events'][0]['event_id'])],corrected)
        self.assertEqual(self.ledger.find('dhruva-v1:2026-09-17'),original)
        self.assertEqual(self.ledger.latest_for_date('2026-09-17'),newer)

    def test_partial_checkpoint_crash_recovers_without_duplicate(self):
        from dhruva import ledger
        real_write = ledger.atomic_write
        def crash(path, raw):
            if path.name == 'checkpoint.json': raise OSError('simulated power loss')
            real_write(path, raw)
        with patch('dhruva.ledger.atomic_write', side_effect=crash):
            with self.assertRaises(OSError): self.ledger.append('one', [event()])
        self.assertEqual(self.ledger.verify()['segments'], 1)
        _, added = self.ledger.append('one', [event()])
        self.assertFalse(added)
        self.ledger.append('two', [event(action='HOLD')])
        self.assertEqual(self.ledger.verify()['segments'], 2)

    def test_snapshot_content_roundtrip_and_corruption(self):
        key = self.ledger.snapshot({'data': [1, 2, None]})
        self.assertEqual(key, self.ledger.snapshot({'data': [1, 2, None]}))
        self.assertEqual(self.ledger.read_snapshot(key), {'data': [1, 2, None]})
        (self.root/'snapshots'/f'{key}.json.gz').write_bytes(b'broken')
        with self.assertRaises(LedgerError): self.ledger.read_snapshot(key)

    def test_validation_rejects_real_money_future_cutoff_and_nan(self):
        for change in ({'execution_mode': 'EXECUTED'}, {'portfolio_nav': float('nan')},
                       {'data_cutoff_at': '2026-09-19T05:00:00+00:00'},
                       {'generated_at': '2026-09-18T05:00:00'}):
            with self.subTest(change=change):
                with self.assertRaises(LedgerError): self.ledger.append('bad', [event(**change)])
        self.assertEqual(self.ledger.verify()['head'], ZERO)


if __name__ == '__main__': unittest.main()
