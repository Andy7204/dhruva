import unittest.mock
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dhruva import forward as F, digest as D, performance as P  # noqa: E402


def book(as_of, curve, pending=None):
    return {'label': 'x', 'as_of': as_of, 'curve': curve, 'weights': {'N50': 1.0},
            'pending_target': pending, 'liquidation_value': curve[-1][2], 'nav': curve[-1][1]}


class ForwardTests(unittest.TestCase):
    def test_record_appends_once_and_flags_revisions(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            books = {'A': book('2026-10-01', [['2026-09-30', 100, 100], ['2026-10-01', 101, 100.5]])}
            self.assertEqual(F.record(books, root, now='t1'), [])
            self.assertEqual(F.record(books, root, now='t2'), [])
            rows = [json.loads(x) for x in (root/'runs/forward/log.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[0]['reconstructed'])
            books['A']['curve'][1] = ['2026-10-01', 101, 99.0]
            self.assertEqual(len(F.record(books, root, now='t3')), 1)
            self.assertEqual(F.history(root).loc['2026-10-01', 'A'], 100.5)

    def test_real_config_books_exist(self):
        from lab import strategies as S
        cfg = F.config()
        for spec in cfg['books'].values():
            self.assertIn(spec['strategy'], S.CANDIDATES)
        self.assertIn(cfg['benchmark'], S.CANDIDATES)

    def test_digest_only_on_new_allocation_or_friday(self):
        quiet = {'A': book('2026-10-06', [['2026-10-06', 1, 1]]), 'N50': book('2026-10-06', [['2026-10-06', 1, 1]])}
        self.assertEqual(D.build({'A': {'weights': {'N50': 1.0}}}, quiet)['kind'], 'NONE')
        quiet['A']['pending_target'] = {'GOLD': 1.0}
        self.assertEqual(D.build({'A': {'weights': {'N50': 1.0}}}, quiet)['kind'], 'CHANGE')
        friday = {'A': book('2026-10-09', [['2026-10-09', 1, 1]])}
        self.assertEqual(D.build({}, friday)['kind'], 'WEEKLY')

    def test_verdicts(self):
        import pandas as pd
        c = {'earliest_verdict_years': 3, 'final_verdict_years': 5, 'pass_min_excess_cagr_pct': 3,
             'max_drawdown_limit_pct': 35, 'early_fail_after_years': 1, 'early_fail_cumulative_shortfall_pct': 15}
        s = lambda d, v: pd.Series(v, index=d)
        self.assertEqual(P.verdict(s(['2026-10-01', '2027-01-01'], [100, 60]), s(['2026-10-01', '2027-01-01'], [100, 100]), c)[0], 'FAIL')
        self.assertEqual(P.verdict(s(['2026-10-01', '2029-10-02'], [100, 160]), s(['2026-10-01', '2029-10-02'], [100, 120]), c)[0], 'PASS')
        self.assertEqual(P.verdict(s(['2026-10-01', '2027-06-01'], [100, 110]), s(['2026-10-01', '2027-06-01'], [100, 100]), c)[0], 'INCONCLUSIVE')


class AppTests(unittest.TestCase):
    def test_app_renders_without_exceptions(self):
        from streamlit.testing.v1 import AppTest
        import ast
        path = Path(__file__).resolve().parents[1]/'streamlit_app.py'
        ast.parse(path.read_text(encoding='utf-8'))  # a syntax error must fail loudly
        app = AppTest.from_file(str(path)).run(timeout=60)
        self.assertEqual(len(app.exception), 0, list(app.exception))
        self.assertGreater(len(app.markdown)+len(app.dataframe), 3)  # the page actually rendered


if __name__ == '__main__':
    unittest.main()


class GuardTests(unittest.TestCase):
    def test_late_start_after_midnight_still_processes_missed_session(self):
        from datetime import datetime
        from dhruva import daily
        from dhruva.calendar import IST
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); (root/'runs/forward').mkdir(parents=True)
            (root/'runs/forward/state.json').write_text(json.dumps({'A': {'as_of': '2026-10-05'}}))
            # 02:10 IST Tuesday: the Monday 2026-10-05 session is complete and already recorded
            done = daily.run(root, datetime(2026, 10, 6, 2, 10, tzinfo=IST))
            self.assertEqual(done['status'], 'SKIPPED_UP_TO_DATE')
            (root/'runs/forward/state.json').write_text(json.dumps({'A': {'as_of': '2026-09-30'}}))
            with unittest.mock.patch('dhruva.marketdata.update', side_effect=RuntimeError('fetch attempted')):
                late = daily.run(root, datetime(2026, 10, 6, 2, 10, tzinfo=IST))
            self.assertEqual(late['session'], '2026-10-05')  # not skipped as "before market close"
            self.assertIn('fetch attempted', late['errors'][0])
