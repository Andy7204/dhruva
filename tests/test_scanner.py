import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner import score as S  # noqa: E402


def fund(rev, ebitda, pat, eps, cfo=120, apat=100):
    q = lambda vals: [[f'2025-{i:02d}-30', v] for i, v in enumerate(vals, 1)]
    return {'quarterlyTotalRevenue': q(rev), 'quarterlyEBITDA': q(ebitda), 'quarterlyNormalizedEBITDA': q(ebitda),
            'quarterlyNetIncome': q(pat), 'quarterlyDilutedEPS': q(eps), 'quarterlyPretaxIncome': q([p*1.33 for p in pat]),
            'quarterlyTaxProvision': q([p*.33 for p in pat]), 'quarterlyTotalUnusualItems': q([0]*5),
            'annualOperatingCashFlow': q([cfo*.8, cfo]), 'annualNetIncome': q([apat*.8, apat]),
            'annualTotalRevenue': q([800, 1000]), 'annualAccountsReceivable': q([100, 110]),
            'annualFreeCashFlow': q([10, 20]), 'annualOrdinarySharesNumber': q([1e7, 1e7]), 'quarterlyOrdinarySharesNumber': q([1e7]*5)}


def frame(growth=0.001, n=300):
    idx = pd.bdate_range('2025-01-01', periods=n)
    c = pd.Series(100*(1+growth)**np.arange(n), index=idx)
    return pd.DataFrame({'close': c, 'volume': 1e6})


class ScoreTests(unittest.TestCase):
    def test_operating_leverage_beats_low_quality_growth(self):
        good = S.fundamentals(fund([100, 105, 110, 118, 125], [15, 16, 18, 20, 22], [8, 9, 10, 12, 14], [1, 1.1, 1.2, 1.4, 1.7]), 100, 10)
        bad = S.fundamentals(fund([100, 120, 140, 160, 185], [15, 15, 16, 16, 16], [8, 8, 8, 8, 8], [1, 1, 1, 1, 1]), 100, 10)
        total = lambda r: sum(S.WEIGHTS[k]*r[0][k] for k in r[0])
        self.assertGreater(total(good), total(bad))
        self.assertIn('low-quality growth: EBITDA lags revenue', bad[2])
        self.assertAlmostEqual(good[1]['incremental_ebitda_margin'], (22-15)/(125-100)*100)

    def test_turnaround_and_missing_data_are_explicit(self):
        parts, x, flags, ok = S.fundamentals(fund([100]*5, [5]*5, [-2, -1, -1, 0, 3], [-.2, -.1, -.1, 0, .3]), 50, 0)
        self.assertTrue(x['turnaround']); self.assertEqual(parts['profit'], 1.)
        parts, x, flags, ok = S.fundamentals({}, 50, 0)
        self.assertFalse(ok)

    def test_only_serious_filings_veto(self):
        self.assertTrue(S._red('resignation of statutory auditor'))
        self.assertTrue(S._red('corporate insolvency resolution process'))
        self.assertFalse(S._red('change in auditors'))
        self.assertFalse(S._red('action(s) taken or orders passed'))

    def test_scan_ranks_and_price_does_not_add_score(self):
        uni = pd.DataFrame({'symbol': ['A', 'B'], 'name': ['A', 'B'], 'industry': ['X', 'X']})
        f = fund([100, 105, 110, 118, 125], [15, 16, 18, 20, 22], [8, 9, 10, 12, 14], [1, 1.1, 1.2, 1.4, 1.7])
        out = S.scan(uni, {'A': frame(0.002), 'B': frame(-0.001)}, {'A': f, 'B': f}, [], news_ok=True, as_of='2026-01-01')
        a, b = out.set_index('symbol').loc['A'], out.set_index('symbol').loc['B']
        # identical fundamentals; valuation differs only through price-based ratios, never through trend
        self.assertEqual(a['revenue_pts'], b['revenue_pts']); self.assertEqual(a['leverage_pts'], b['leverage_pts'])


class UnderwriterTests(unittest.TestCase):
    def test_capital_credits_monthly_and_applies_only_confirmed_trades(self):
        from underwriter import run as U
        with tempfile.TemporaryDirectory() as t:
            with patch.object(U, 'INF', Path(t)):
                self.assertEqual(U.capital('2026-10-01')['cash_inr'], 10000)
                self.assertEqual(U.capital('2026-10-15')['cash_inr'], 10000)
                self.assertEqual(U.capital('2026-11-02')['cash_inr'], 20000)
                (Path(t)/'confirmed_trades.jsonl').write_text(json.dumps({'date': '2026-11-03', 'symbol': 'X', 'side': 'BUY', 'qty': 10, 'price': 500, 'fees': 20})+'\n')
                cap = U.capital('2026-11-03')
                self.assertEqual(cap['cash_inr'], 20000-5020); self.assertEqual(cap['holdings']['X']['qty'], 10)
                self.assertEqual(U.capital('2026-11-04')['cash_inr'], 20000-5020)  # not applied twice

    def test_review_triggers(self):
        from underwriter import run as U
        rec = {'reviews': [{'date': '2026-10-01', 'stage2_score': 80}]}
        row = {'symbol': 'X', 'stage2_score': 82}
        self.assertEqual(U.due(row, None, '2026-10-02', {}), 'first review')
        self.assertIsNone(U.due(row, rec, '2026-10-02', {}))
        self.assertIn('score', U.due({'symbol': 'X', 'stage2_score': 86}, rec, '2026-10-02', {}))
        self.assertIn('filing', U.due(row, rec, '2026-10-05', {'X': [{'time': '2026-10-04 10:00', 'desc': 'Investor Presentation'}]}))
        self.assertEqual(U.due(row, rec, '2026-11-01', {}), '30-day refresh')


if __name__ == '__main__':
    unittest.main()
