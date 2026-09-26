import copy
import json
from pathlib import Path
import tempfile
import unittest
import hashlib
from unittest.mock import patch

import pandas as pd

from dhruva.run_daily import main
from qlab import orchestrator as O


class PipelineTests(unittest.TestCase):
    def test_cli_keeps_guard_for_cache_mode(self):
        with patch('dhruva.run_daily.run', return_value={'status': 'SKIPPED_NOT_DUE'}) as run:
            self.assertEqual(main(['--no-refresh'])['status'], 'SKIPPED_NOT_DUE')
            run.assert_called_once_with(refresh=False)

    def test_missed_sessions_replayed_in_order_and_repeat_does_not_step(self):
        cfg = {'paper': {'inception_days_back': 0}, 'starting_capital': 1000}
        cal = pd.to_datetime(['2026-09-21', '2026-09-22', '2026-09-23'])
        state = {'processed_through': '2026-09-18', 'as_of':'2026-09-18'}
        seen = []
        def step(st, panel, date, cfg, regime, factor):
            seen.append(str(date.date())); st['as_of'] = str(date.date())
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'RUNS', Path(tmp)):
            with patch.object(O.LB, 'step', side_effect=step), patch.object(O.E, '_prices_at', return_value={}):
                args = (cfg, 'test', {}, pd.Series(True,index=cal), pd.Series(1.,index=cal), cal)
                O._run_livebook(*args, persist=False, state=state)
                self.assertEqual(seen, ['2026-09-21', '2026-09-22', '2026-09-23'])
                O._run_livebook(*args, persist=False, state=state)
                self.assertEqual(len(seen), 3)

    def test_missing_regime_is_fatal_before_step(self):
        cal = pd.to_datetime(['2026-09-23'])
        cfg = {'paper': {'inception_days_back': 0}, 'starting_capital': 1000}
        with tempfile.TemporaryDirectory() as tmp, patch.object(O, 'RUNS', Path(tmp)):
            with patch.object(O.LB, 'step') as step:
                with self.assertRaisesRegex(ValueError, 'Missing market regime'):
                    O._run_livebook(cfg, 'test', {}, None, None, cal, persist=False,
                                   state={'processed_through': '2026-09-22'})
                step.assert_not_called()

    def test_full_pipeline_recovers_partial_publication_and_duplicates(self):
        from dhruva.ledger import Ledger
        cfg = {'starting_capital':1000, 'base_currency':'INR', 'universe':['TEST'],
               'data':{'backtest_range':'5y'}, 'regime':{'benchmark':'INDEX'},
               'paper':{'inception_days_back':0},
               'books':{'balanced':{'capital':700},'aggressive':{'capital':300}}}
        cfg['tax']=json.loads(Path('config.json').read_text(encoding='utf-8'))['tax']
        cfg['income_receipts']=[{'id':'income-fixture','book':'balanced','symbol':'TEST',
            'gross':100.,'withheld':10.,'effective_date':'2026-09-23','taxable_date':'2026-09-23',
            'retrieved_at':'2026-09-23T12:00:00+00:00','mode':'cash',
            'source_url':'https://example.org/fixture','source_path':'source.txt',
            'source_sha256':hashlib.sha256(b'fixture').hexdigest()}]
        dates = pd.to_datetime(['2026-09-21','2026-09-22','2026-09-23'])
        frame = pd.DataFrame({'adjclose':[100.,101.,102.]},index=dates)
        calls = []
        def step(st, panel, date, config, regime, factor, **kwargs):
            calls.append((st['name'], str(date.date())))
            st['as_of'] = str(date.date())
            st['price_convention']='actual_quoted_units'
            st['history'].append([st['as_of'], st['capital']])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); runs = root/'runs'; runs.mkdir()
            (root/'source.txt').write_bytes(b'fixture')
            for name, capital in [('balanced',700),('aggressive',300)]:
                st = O.LB.new_livebook({'starting_capital':capital}, name)
                st.update(as_of='2026-09-18', processed_through='2026-09-18', history=[['2026-09-18',capital]])
                (runs/f'livebook_{name}.json').write_text(json.dumps(st))
            from contextlib import ExitStack
            with ExitStack() as stack:
                for target, value in [('PROJECT_ROOT',root),('RUNS',runs)]: stack.enter_context(patch.object(O,target,value))
                stack.enter_context(patch('dhruva.freeze.verify_v1'))
                stack.enter_context(patch('dhruva.evidence.subprocess.check_output',return_value='fixture'))
                stack.enter_context(patch.object(O.D,'load_config',return_value=cfg))
                stack.enter_context(patch.object(O.D,'get_universe',return_value={'TEST':frame}))
                stack.enter_context(patch.object(O.D,'get_history',return_value=frame))
                stack.enter_context(patch.object(O.E,'build_panel',return_value={'TEST':frame}))
                stack.enter_context(patch.object(O.I,'enrich',return_value=frame))
                stack.enter_context(patch('dhruva.data_quality.validate_inputs',return_value=({'TEST':frame},frame,{'status':'VALID','coverage':1.,'excluded':{}})))
                stack.enter_context(patch.object(O.E,'regime_series',return_value=pd.Series(True,index=dates)))
                stack.enter_context(patch.object(O.E,'regime_factor_series',return_value=pd.Series(1.,index=dates)))
                stack.enter_context(patch.object(O.LB,'step',side_effect=step))
                stack.enter_context(patch('qlab.narrator.narrate',return_value='Fixture prose'))
                stack.enter_context(patch.object(O.R,'build_multi_dashboard',return_value='fixture.html'))
                stack.enter_context(patch('qlab.notify.send_telegram'))
                save = O._save_book
                def interrupted(name, state):
                    if name == 'aggressive': raise OSError('fixture publication interruption')
                    save(name,state)
                with patch.object(O,'_save_book',side_effect=interrupted):
                    with self.assertRaisesRegex(OSError,'publication interruption'):
                        O.daily_run(refresh=False,verbose=False)
                # Both books committed before one projection failed. Retry restores
                # that exact bundle, then processes only the remaining two days.
                result = O.daily_run(refresh=False,verbose=False)
                self.assertEqual(len(calls),6)
                ledger = Ledger(runs/'ledger/dhruva_v1'); before=ledger.verify()
                repeated = O.daily_run(refresh=False,verbose=False)
                self.assertEqual(before,ledger.verify())
                self.assertEqual(result['results'],repeated['results'])
                self.assertEqual(repeated['new_evaluations'],0)
                self.assertEqual(len(calls),6)
                recovered = ledger.find('dhruva-v1:2026-09-21')['payload']['events']
                self.assertTrue(all(e['execution_status']=='RECOVERY_RECONSTRUCTION' for e in recovered))
                self.assertEqual(before['segments'],3)
                balanced=next(r['state'] for r in result['results'] if r['name']=='balanced')
                self.assertEqual(balanced['history'][-1][1],768.8)
                self.assertEqual(len(balanced['income_receipts']),1)
                cfg['income_receipts'].append(dict(cfg['income_receipts'][0],id='late-amendment'))
                with self.assertRaisesRegex(ValueError,'explicit ledger correction'):
                    O.daily_run(refresh=False,verbose=False)
                self.assertEqual(before,ledger.verify())


if __name__ == '__main__': unittest.main()
