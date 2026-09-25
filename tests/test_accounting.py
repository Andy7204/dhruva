import json
from pathlib import Path
import unittest
from qlab import tax, lots, costs, livebook


class AccountingTests(unittest.TestCase):
    def setUp(self): self.cfg=json.loads(Path('config.json').read_text(encoding='utf-8'))

    def sale(self,gain,symbol='TEST',days=400):
        return {'symbol':symbol,'gain':gain,'holding_days':days,'exit_date':'2026-09-24'}

    def test_shared_exemption_reserve_reduces_nav(self):
        states={n:{'realized_sales':[self.sale(100000)],'cash':100000,'holdings':{}} for n in ('a','b')}
        total,_=tax.reserve_accounts(states,self.cfg)
        self.assertEqual(total,9750.)
        self.assertEqual(sum(s['tax_reserve'] for s in states.values()),total)
        self.assertEqual(sum(livebook.total_value(s,{}) for s in states.values()),200000-total)

    def test_fifo_partial_lots_and_stt_excluded_from_tax_basis(self):
        h={};charges={'total':10.,'stt':2.}
        lots.buy(h,10,1000,charges,'2025-01-01','a')
        lots.buy(h,10,2000,charges,'2026-01-01','b')
        sales=lots.sell(h,15,3000,charges,'2026-09-24','TEST','sell')
        self.assertEqual([(r['lot_id'],r['qty']) for r in sales],[('a',10),('b',5)])
        self.assertEqual(h['qty'],5)
        self.assertEqual(h['cost'],1005.)
        self.assertAlmostEqual(sum(r['gain'] for r in sales)-sum(r['economic_gain'] for r in sales),5.,places=2)
        self.assertTrue(tax.is_long(sales[0]));self.assertFalse(tax.is_long(sales[1]))

    def test_taxonomy_independent_of_book_and_debt_holding_period(self):
        self.cfg['defensive_basket']={}
        self.assertFalse(tax.is_equity('GOLDBEES.NS',self.cfg))
        self.assertTrue(tax.is_equity('INDIGRID.NS',self.cfg))
        total,_=tax.accrued_tax([self.sale(10000,'LIQUIDBEES.NS',900)],self.cfg)
        self.assertEqual(total,3120.)

    def test_shared_fifo_sale_uses_older_other_sleeve_tax_lot(self):
        import pandas as pd
        from unittest.mock import patch
        state=livebook.new_livebook(self.cfg,'newer')
        state.update(step_count=2,as_of='2026-09-21')
        own={'kind':'stock','stop':0,'settle_date':'2026-09-02'}
        charges={'total':0.,'stt':0.}
        lots.buy(own,10,2000,charges,'2026-09-01','newer:1')
        state['holdings']['TEST']=own
        state['orders']=[{'id':'newer:2','symbol':'TEST','side':'SELL','status':'scheduled','decided_date':'2026-09-21'}]
        inventory={'TEST':{}}
        lots.buy(inventory['TEST'],10,1000,charges,'2025-01-01','older:1')
        lots.buy(inventory['TEST'],10,2000,charges,'2026-09-01','newer:1')
        day=pd.Timestamp('2026-09-22')
        panel={'TEST':pd.DataFrame({'adj_open':[300.],'adj_low':[300.],'adjclose':[300.]},index=[day])}
        self.cfg['slippage_bps']=0
        with patch('qlab.livebook.C.order_charges',return_value=charges):
            livebook.step(state,panel,day,self.cfg,False,1.,tax_inventory=inventory)
        self.assertEqual(state['realized_sales'][0]['lot_id'],'older:1')
        self.assertEqual(state['realized_sales'][0]['gain'],2000.)
        self.assertEqual(state['realized_pnl'],1000.)
        self.assertEqual(inventory['TEST']['lots'][0]['id'],'newer:1')

    def test_capital_loss_setoff_and_year_isolation(self):
        sales=[self.sale(-10000,'GOLDBEES.NS',30),self.sale(20000,'TEST',30)]
        self.assertEqual(tax.accrued_tax(sales,self.cfg)[0],2080.)
        sales[0]['exit_date']='2027-09-24'
        self.assertEqual(tax.accrued_tax(sales,self.cfg)[0],4160.)

    def test_costs_include_dp_gst_ipft_and_instrument_stt(self):
        cfg=self.cfg['costs']
        c=costs.order_charges(10000,'sell','delivery','NSE',cfg,'GOLDBEES.NS')
        self.assertEqual(c['stt'],0)
        self.assertEqual(c['dp'],20)
        self.assertAlmostEqual(c['ipft'],.01)
        self.assertAlmostEqual(c['gst'],.18*(10+20+.297+.01+.01))
        self.assertEqual(costs.order_cost(0,'sell','TEST','delivery',cfg),0)
