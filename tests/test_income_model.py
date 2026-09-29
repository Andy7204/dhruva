import copy
import unittest
from datetime import datetime
from qlab.income_model import accrue, accrue_cash, scenario_net
from dhruva.calendar import run_due, expected_date, IST


class IncomeModelTests(unittest.TestCase):
    def test_prospective_weekend_tax_and_repeat_safety(self):
        prior={'as_of':'2026-10-02','holdings':{'LIQUIDBEES.NS':{
            'settle_date':'2026-09-18','lots':[{'qty':3}]}},'cash':50.}
        state=copy.deepcopy(prior)
        accrue(state,prior,'2026-10-05',.312)
        model=state['income_scenario']
        self.assertAlmostEqual(model['gross'],3000*.04*3/365)
        self.assertAlmostEqual(model['net'],model['gross']*.688)
        self.assertEqual(state['cash'],50.)
        self.assertEqual(state['holdings'],prior['holdings'])
        saved=copy.deepcopy(state)
        accrue(state,prior,'2026-10-05',.312)
        self.assertEqual(state,saved)

    def test_no_history_backfill_or_unsettled_exposure(self):
        prior={'as_of':'2026-09-28','holdings':{'LIQUIDBEES.NS':{
            'settle_date':'2026-10-02','lots':[{'qty':3}]}}}
        state=copy.deepcopy(prior)
        accrue(state,prior,'2026-09-29',.312)
        self.assertNotIn('income_scenario',state)
        accrue(state,prior,'2026-10-01',.312)
        self.assertEqual(state['income_scenario']['gross'],0.)

    def test_idle_cash_yield_is_prospective_and_outside_nav(self):
        prior={'as_of':'2026-10-02','cash':36500.,'holdings':{},'history':[['2026-10-02',36500.]]}
        state=copy.deepcopy(prior); state['as_of']='2026-10-05'
        accrue_cash(state,prior,'2026-10-05',.312)
        model=state['cash_yield_scenario']
        self.assertAlmostEqual(model['gross'],36500*.04*3/365)
        self.assertAlmostEqual(scenario_net(state),model['gross']*.688)
        self.assertEqual((state['cash'],state['history']),(prior['cash'],prior['history']))
        saved=copy.deepcopy(state); accrue_cash(state,prior,'2026-10-05',.312)
        self.assertEqual(state,saved)
        early=copy.deepcopy(prior); early['as_of']='2026-09-28'
        fresh={}; accrue_cash(fresh,early,'2026-09-29',.312)
        self.assertNotIn('cash_yield_scenario',fresh)

    def test_special_session_uses_own_completed_time(self):
        # Synthetic timing only, not a claim about actual Muhurat hours.
        cfg={'valid_from':'2026-11-01','valid_through':'2026-11-30','holidays':[],
             'special_sessions':{'2026-11-08':{'completed_after_ist':'21:00',
                  'source_url':'https://example.org/synthetic-test'}}}
        early=datetime(2026,11,8,18,30,tzinfo=IST)
        late=datetime(2026,11,8,22,0,tzinfo=IST)
        self.assertFalse(run_due(early,cfg)[0])
        self.assertEqual(expected_date(early,cfg),'2026-11-06')
        self.assertTrue(run_due(late,cfg)[0])
        self.assertEqual(expected_date(late,cfg),'2026-11-08')
