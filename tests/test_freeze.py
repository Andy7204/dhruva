import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from dhruva.freeze import ROOT, FrozenStrategyChanged, verify_v1


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/'strategies/dhruva_v1', self.root/'strategies/dhruva_v1')
        self.manifest = json.loads((self.root/'strategies/dhruva_v1/strategy_manifest.yaml').read_bytes())
        for path in self.manifest['active_guard_files']:
            target = self.root/path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/'strategies/dhruva_v1/snapshot'/path, target)

    def test_original_archive_and_active_code_verify(self):
        self.assertEqual(verify_v1(self.root, check_active=True)['strategy_version'], '1.0')

    def test_source_config_universe_and_history_mutations_rejected(self):
        paths = ['qlab/livebook.py', 'config.json', 'data/nifty500.txt',
                 'strategies/dhruva_v1/snapshot/runs/livebook_balanced.json']
        for path in paths:
            with self.subTest(path=path):
                target = self.root/path
                original = target.read_bytes()
                target.write_bytes(original+b'\nchanged')
                with self.assertRaises(FrozenStrategyChanged):
                    verify_v1(self.root, check_active=True)
                target.write_bytes(original)

    def test_manifest_tamper_and_missing_archive_rejected(self):
        target = self.root/'strategies/dhruva_v1/strategy_manifest.yaml'
        target.write_bytes(target.read_bytes()+b' ')
        with self.assertRaises(FrozenStrategyChanged):
            verify_v1(self.root)
        target.unlink()
        with self.assertRaises(FrozenStrategyChanged):
            verify_v1(self.root)

    def test_windows_checkout_newlines_are_equivalent(self):
        for path in self.manifest['active_guard_files']:
            target = self.root/path
            target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        verify_v1(self.root, check_active=True)

    def test_authorized_active_repairs_leave_archive_verifiable(self):
        (self.root/'qlab/livebook.py').write_text('# authorized in-place repair')
        verify_v1(self.root)
        with self.assertRaises(FrozenStrategyChanged):
            verify_v1(self.root, check_active=True)

    def test_daily_run_rejects_changed_version_before_fetch(self):
        from qlab.orchestrator import daily_run
        with patch('dhruva.freeze.verify_v1', side_effect=FrozenStrategyChanged('fixture')):
            with patch('qlab.orchestrator.D.update_universe') as fetch:
                with self.assertRaises(FrozenStrategyChanged):
                    daily_run()
                fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
