import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
from qlab import livebook as L


class LiveExecutionTests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads(Path('config.json').read_text(encoding='utf-8'))
        self.cfg['slippage_bps']=0
        self.state=L.new_livebook(self.cfg,'fixture')
        self.state.update(step_count=2,as_of='2026-09-21')
        self.date=pd.Timestamp('2026-09-22')
        self.panel={'TEST':pd.DataFrame({'adj_open':[80.],'adj_low':[75.],
                    'adjclose':[82.]},index=[self.date])}

    def hold(self):
        self.state['holdings']['TEST']={'qty':10,'cost':1000.,'avg':100.,
            'kind':'stock','stop':90.,'acquired':'2026-09-01','settle_date':'2026-09-02',
            'lots':[{'id':'old','qty':10,'economic_cost':1000.,'tax_cost':1000.,'acquired':'2026-09-01'}]}

    def step(self):
        with patch('qlab.livebook.C.order_charges',return_value={'total':0.,'stt':0.}):
            L.step(self.state,self.panel,self.date,self.cfg,False,1.)

    def test_gap_stop_and_restart_safe_permanent_journal(self):
        self.hold(); self.step()
        order=copy.deepcopy(self.state['orders'][0])
        self.assertEqual(order['fill_price'],80.)
        self.state=json.loads(json.dumps(self.state))
        self.assertNotEqual(L._oid(self.state),order['id'])
        self.date=pd.Timestamp('2026-09-23');self.panel={}
        self.step()
        self.assertEqual(self.state['orders'][0]['id'],order['id'])
        self.assertEqual(self.state['orders'][0]['status'],'settled')

    def test_same_day_intent_not_filled_and_duplicate_noop(self):
        self.state['orders']=[{'id':'fixture:1','side':'BUY','symbol':'TEST','kind':'stock',
            'status':'scheduled','decided_date':'2026-09-22','target_value':1000}]
        self.step(); before=copy.deepcopy(self.state); self.step()
        self.assertEqual(self.state,before)
        self.assertEqual(self.state['orders'][0]['status'],'scheduled')

    def test_missing_held_prices_fails_without_mutation(self):
        self.hold(); self.panel={}; before=copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'Missing held-symbol'):
            self.step()
        self.assertEqual(self.state,before)

    def test_sale_proceeds_do_not_fund_same_day_buys(self):
        self.hold();self.state['holdings']['TEST']['stop']=0
        self.state['cash']=0
        self.panel['OTHER']=self.panel['TEST'].copy()
        self.state['orders']=[
            {'id':'fixture:1','side':'SELL','symbol':'TEST','kind':'stock','status':'scheduled','decided_date':'2026-09-21'},
            {'id':'fixture:2','side':'BUY','symbol':'OTHER','kind':'stock','status':'scheduled','decided_date':'2026-09-21','target_value':800}]
        self.step()
        self.assertEqual(self.state['cash'],0)
        self.assertNotIn('OTHER',self.state['holdings'])
        self.assertEqual(self.state['receivables'][0]['amount'],800)
        self.assertEqual(L.total_value(self.state,{}),800)
        self.date=pd.Timestamp('2026-09-23');self.panel={};self.step()
        self.assertEqual(self.state['cash'],800)
        self.assertEqual(self.state['receivables'],[])

    def test_settlement_holiday_weekend_and_expiry(self):
        self.assertEqual(L._settle_date('2026-10-01',1),'2026-10-05')
        self.assertEqual(L._settle_date('2026-09-11',1),'2026-09-15')
        with self.assertRaisesRegex(ValueError,'calendar coverage'):
            L._settle_date('2026-10-30',1)

    def test_stock_fill_respects_weight_limit_after_costs(self):
        self.cfg['sleeves']['long_term']['max_pos_weight']=.12
        self.state['orders']=[{'id':'fixture:1','side':'BUY','symbol':'TEST','kind':'stock',
            'status':'scheduled','decided_date':'2026-09-21','target_value':100000}]
        self.step()
        qty=self.state['holdings']['TEST']['qty']
        self.assertLessEqual(qty*80,self.state['capital']*.12)

    def test_quoted_execution_does_not_buy_adjusted_price_units(self):
        frame=self.panel['TEST']
        frame['open']=160.;frame['low']=150.;frame['close']=164.
        self.state['orders']=[{'id':'fixture:1','side':'BUY','symbol':'TEST','kind':'stock',
            'status':'scheduled','decided_date':'2026-09-21','target_value':1600}]
        self.step()
        self.assertEqual(self.state['holdings']['TEST']['qty'],10)
        self.assertEqual(self.state['orders'][0]['fill_price'],160.)
        self.assertEqual(self.state['last_raw_prices']['TEST'],164.)
        self.assertEqual(self.state['price_convention'],'actual_quoted_units')

    def test_revised_raw_history_fails_before_mutating_position(self):
        self.hold()
        self.state.update(price_convention='actual_quoted_units',last_raw_prices={'TEST':100.})
        self.panel['TEST']=pd.DataFrame({'open':[50.,51.],'low':[49.,50.],
            'close':[50.,52.],'adjclose':[50.,52.]},index=pd.to_datetime(['2026-09-21','2026-09-22']))
        before=copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'corporate-action reconciliation'):
            self.step()
        self.assertEqual(self.state,before)

    def test_legacy_entry_adjustment_requires_explicit_reconciliation(self):
        self.hold()
        self.panel['TEST']=pd.DataFrame({'open':[100.,100.,100.],'low':[100.,100.,100.],
            'close':[100.,100.,100.],'adjclose':[50.,100.,100.]},
            index=pd.to_datetime(['2026-09-01','2026-09-21','2026-09-22']))
        before=copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'Legacy adjusted units'):
            self.step()
        self.assertEqual(self.state,before)

    def test_all_cash_breaker_can_reset_only_after_cooldown_and_trend(self):
        self.state.update(cash=70000,peak_value=100000,breaker=True,breaker_trigger_step=1,step_count=63)
        with patch('qlab.livebook.E._momentum_top_set',return_value=[]),patch('qlab.livebook.E._allocation',return_value=(1.,{})):
            L.step(self.state,{},self.date,self.cfg,False,1.)
            self.assertTrue(self.state['breaker'])
            L.step(self.state,{},pd.Timestamp('2026-09-23'),self.cfg,True,1.)
        self.assertFalse(self.state['breaker'])
        self.assertEqual(self.state['peak_value'],70000)
