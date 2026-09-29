import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import engine as E, strategies as S  # noqa: E402


def prices(n=600, growth=0.0004):
    cal = pd.bdate_range('2020-01-01', periods=n)
    base = pd.Series([(1+growth)**i for i in range(n)], index=cal)
    return pd.DataFrame({'N50': 100*base, 'MOM30': 100*base**1.5, 'GOLD': 100*base**0.5, 'LIQ': 100*base**0.2})


class EngineTests(unittest.TestCase):
    def test_buy_and_hold_tax_matches_hand_calculation(self):
        p = prices(); st = S.hold('N50'); st.start = 0
        curve, acct, _ = E.run(p, st, 0, len(p)-1, capital=100000, liq_every=1)
        value = curve['nav'].iloc[-1]
        units = acct.lots['N50'][0].qty; cost = acct.lots['N50'][0].cost
        gain = units*p['N50'].iloc[-1]-units*cost
        expected = value-gain*.125*1.04  # long-term equity, no exemption
        self.assertAlmostEqual(curve['liq'].iloc[-1], expected, delta=1)

    def test_one_session_execution_lag_and_no_lookahead(self):
        p = prices(); st = S.hold('N50'); st.start = 0
        curve, acct, log = E.run(p, st, 0, 5, capital=100000)
        self.assertEqual(acct.lots['N50'][0].day, p.index[1])  # decided day 0, filled day 1
        future = p.copy(); future.iloc[10:] *= 3
        st2 = S.hold('N50'); st2.start = 0
        c2, _, _ = E.run(future, st2, 0, 5, capital=100000)
        pd.testing.assert_series_equal(curve['nav'], c2['nav'])

    def test_short_term_sale_taxed_at_twenty_percent(self):
        acct = E.Account(cash=0.)
        acct.realized[2024] = {'st': 1000., 'lt': 0., 'slab': 0.}
        self.assertAlmostEqual(E.settle_tax(acct, 2024), 1000*.20*1.04)

    def test_losses_carry_forward(self):
        acct = E.Account(cash=0.)
        acct.realized[2023] = {'st': -500., 'lt': 0., 'slab': 0.}
        self.assertEqual(E.settle_tax(acct, 2023), 0)
        acct.realized[2024] = {'st': 800., 'lt': 0., 'slab': 0.}
        self.assertAlmostEqual(E.settle_tax(acct, 2024), 300*.20*1.04)

    def test_static_rebalances_on_schedule(self):
        p = prices(); st = S.static({'N50': .5, 'GOLD': .5}, every=252); st.start = 0
        _, _, log = E.run(p, st, 0, 520)
        self.assertEqual([d for d, _ in log], [p.index[0], p.index[252], p.index[504]])


if __name__ == '__main__':
    unittest.main()
