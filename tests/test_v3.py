import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner import events as EV, discovery as DS  # noqa: E402
from underwriter import state as ST  # noqa: E402

STL_ORDER = """Annexure A 1. name of the entity awarding the order(s)/contract(s) A hyperscale partner
2. significant terms i) Allocation of optical connectivity products to be supplied in each Financial Year (FY)
starting from FY27 to FY29. The total potential value of the contract over its tenure is estimated at ~USD 1.11 billion
3. whether order(s) / contract(s) have been awarded by domestic/ international entity International"""
DOMESTIC = """received an order from Domestic Telecom Operator. 3. whether awarded by domestic/international entity Domestic
4. Size of order(s)/contract(s) Rs. 960 crores 5. time period by which to be executed within 24 months. Purchase order."""


class EventTests(unittest.TestCase):
    def test_stl_award_sized_and_haircut(self):
        f = EV.order_facts(STL_ORDER, 88.5)
        self.assertAlmostEqual(f['value_cr'], 1.11*1000*88.5/10, places=0)
        self.assertEqual((f['years'], f['firmness'], f['customer'], f['tier1_customer']), (3, 0.5, 'international', True))

    def test_domestic_firm_order(self):
        f = EV.order_facts(DOMESTIC, 88.5)
        self.assertEqual((f['value_cr'], f['years'], f['firmness'], f['customer']), (960.0, 2.0, 1.0, 'domestic'))

    def test_prices_are_not_contract_sizes(self):
        self.assertEqual(EV.amounts('at a price of Rs. 110 per warrant', 88), [])
        self.assertEqual(EV.amounts('USD 12 per unit', 88), [])

    def test_fast_lane_and_surveillance_join(self):
        idx = pd.bdate_range('2026-05-01', periods=30)
        prices = {'X': pd.DataFrame({'close': np.linspace(400, 450, 30), 'volume': 1e6}, index=idx)}
        fund = {'X': {'quarterlyTotalRevenue': [[f'2026-0{i}-30', 1.2e10] for i in range(1, 5)],
                      'quarterlyOrdinarySharesNumber': [['2026-03-31', 4.88e8]]}}
        filings = [{'symbol': 'X', 'desc': EV.ORDER, 'time': '2026-05-22 15:48:00', 'url': None, 'text': STL_ORDER},
                   {'symbol': 'X', 'desc': 'Spurt in Volume', 'time': '2026-05-21 10:00:00'}]
        with patch.object(EV, 'pdf_text', lambda url: ''):
            ev = EV.evaluate(filings, fund, prices, 88.5)
        self.assertTrue(ev['material'].iloc[0])
        self.assertGreater(ev['order_intensity'].iloc[0], 0.2)
        self.assertEqual(EV.surveillance_join(filings, ev), {'X'})


class DiscoveryTests(unittest.TestCase):
    def test_order_capacity_promoter_drive_discovery(self):
        ev = pd.DataFrame([
            {'symbol': 'X', 'date': '2026-05-22', 'desc': EV.ORDER, 'order_intensity': 0.34, 'tier1_customer': True},
            {'symbol': 'X', 'date': '2026-02-07', 'desc': 'Preferential issue', 'promoter': True, 'promoter_pct_mcap': 10.0, 'price_ratio': 0.92},
            {'symbol': 'X', 'date': '2026-09-03', 'desc': 'Capacity addition', 'capacity_pct': 50}])
        score, x, pts = DS.features('X', {}, ev, '2026-09-30')
        self.assertEqual(pts['capacity'], 15); self.assertEqual(pts['promoter_conviction'], 15)
        self.assertEqual(pts['tier1_customer'], 10)
        early, _, _ = DS.features('X', {}, ev, '2026-03-01')  # only the February warrants were public then
        self.assertEqual(early, 15)


class StateTests(unittest.TestCase):
    base = {'score': {'total': 60}, 'discovery_judgement': 75, 'ev_2y_pct': 40, 'bear_downside_pct': -30,
            'hard_numeric_fact': True, 'hard_numeric_fact_text': 'order 34% of revenue', 'risk': {'governance': 'LOW'},
            'new_evidence_type': 'order'}

    def test_starter_then_build_needs_new_evidence_type(self):
        pos = {}
        with tempfile.TemporaryDirectory() as t, patch.object(ST, 'INF', Path(t)):
            self.assertEqual(ST.apply('X', dict(self.base), pos, '2026-05-22', 441, 72)[:2], ('STARTER', 2500))
            same = dict(self.base)  # same evidence type again: no add on price alone
            self.assertEqual(ST.apply('X', same, pos, '2026-06-20', 600, 72)[1], 0)
            new = dict(self.base, new_evidence_type='reported_revenue', ev_2y_pct=30)
            self.assertEqual(ST.apply('X', new, pos, '2026-07-24', 550, 72)[:2], ('BUILD', 3000))

    def test_caps_time_stop_trim_and_exit(self):
        pos = {f'S{i}': {'state': 'STARTER', 'entries': [{'date': '2026-05-01', 'inr': 2500, 'stage': 'STARTER'}], 'evidence': []} for i in range(4)}
        self.assertEqual(ST.gate('X', self.base, pos, '2026-06-02', 100, 72)[0], 'RESEARCH')  # 4 starters open
        old = {'X': {'state': 'STARTER', 'since': '2026-01-01', 'evidence': [{'type': 'order'}], 'entries': [{'date': '2026-01-01', 'inr': 2500, 'stage': 'STARTER'}]}}
        self.assertEqual(ST.gate('X', dict(self.base, new_evidence_type=None), old, '2026-08-01', 100, 72)[0], 'EXIT')
        held = {'X': {'state': 'BUILD', 'since': '2026-07-01', 'evidence': [], 'entries': [{'date': '2026-07-01', 'inr': 5500, 'stage': 'BUILD'}]}}
        self.assertEqual(ST.gate('X', dict(self.base, bull_value_per_share=800), held, '2026-10-01', 955, 72)[0], 'TRIM')
        self.assertEqual(ST.gate('X', dict(self.base, kill_condition_triggered='orders cancelled'), held, '2026-10-01', 500, 72)[0], 'EXIT')


class AuditTests(unittest.TestCase):
    def test_movers_and_diagnosis(self):
        from scanner import audit as A
        idx = pd.bdate_range('2026-01-01', periods=200)
        frames = {'UP': pd.DataFrame({'close': np.r_[np.full(140, 100.), np.linspace(100, 200, 60)]}, index=idx),
                  'FLAT': pd.DataFrame({'close': np.full(200, 100.)}, index=idx)}
        bench = pd.Series(1000., index=idx)
        with patch.object(A, 'benchmark', lambda: bench):
            m = A.movers(frames, str(idx[-1].date()))
        self.assertEqual(list(m['symbol']), ['UP'])
        why, _ = A.diagnose(m.iloc[0], {'FLAT'}, pd.DataFrame(columns=['date', 'symbol', 'score', 'discovery']), pd.DataFrame(), pd.DataFrame())
        self.assertEqual(why, 'not in universe')


if __name__ == '__main__':
    unittest.main()
