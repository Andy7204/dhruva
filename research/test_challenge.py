"""Accounting / causality checks for the isolated challenge study."""
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from challenge import Book, Trial, clean, D, E, I, Market, VARIANTS, ETF


def synthetic(prices, opens=None):
    m=Market.__new__(Market)
    m.cfg=D.load_config()
    m.cal=pd.bdate_range('2022-01-03',periods=len(prices))
    p=pd.Series(prices,index=m.cal,dtype=float)
    o=pd.Series(opens if opens is not None else prices,index=m.cal,dtype=float)
    m.bench=pd.DataFrame({'adjclose':p})
    m.cols={k:pd.DataFrame({ETF:v},index=m.cal) for k,v in
        {'adjclose':p,'adj_open':o,'adj_low':np.minimum(o,p),
         'atr14':p*.01,'sma200':p.rolling(200).mean(),'vol20':p*0+.3}.items()}
    m.marks=m.cols['adjclose'].ffill()
    m.factor=np.ones(len(p))
    m.stock_set=set()
    m.gates={n:(p>p.rolling(n).mean()).to_numpy() for n in [50,100,200]}
    m.gates[0]=np.ones(len(p),dtype=bool)
    return m


class AccountingTests(unittest.TestCase):
    def test_next_open_not_signal_close(self):
        m=synthetic([100,80,90],[100,75,90])
        t=Trial(m,'index_hold',0,2,cost_mult=0,tax=False).run()
        trade=t.trades[0]
        self.assertEqual((trade['i'],trade['price']),(1,75))
        self.assertEqual(t.history[0]['nav'],100000)

    def test_gap_stop_worse_open(self):
        m=synthetic([100,80,80],[100,80,80])
        t=Trial(m,'index_hold',0,2,cost_mult=0,tax=False)
        b=t.books[0]; b.invested_once=True
        t.buy(b,ETF,10000,100,0,stop=90)
        t.run()
        sale=next(x for x in t.trades if x['side']=='sell')
        self.assertEqual(sale['price'],80)
        self.assertEqual(t.gap_stops,1)

    def test_proceeds_unavailable_until_next_session(self):
        m=synthetic([100,100,100])
        t=Trial(m,'index_hold',0,2,cost_mult=0,tax=False); b=t.books[0]
        t.buy(b,ETF,100000,100,0)
        t.sell(b,ETF,b.qty(ETF),100,1)
        self.assertEqual(b.cash,1000)
        self.assertEqual(b.receivables,[(2,99000)])
        t.buy(b,ETF,100000,100,1)
        self.assertLessEqual(b.qty(ETF),10)

    def test_tax_reduces_nav_and_fifo_basis(self):
        m=synthetic([100,200,200])
        t=Trial(m,'index_hold',0,2,cost_mult=0)
        b=t.books[0]
        t.buy(b,ETF,10000,100,0); t.buy(b,ETF,10000,200,1)
        t.sell(b,ETF,100,200,2)
        self.assertAlmostEqual(t.sales[0]['gain'],10000)
        self.assertEqual(t.tax,2000)
        self.assertEqual(b.qty(ETF),50)
        self.assertAlmostEqual(b.value(m,2)-t.tax,108000)

    def test_shared_exemption(self):
        m=synthetic([100]*400)
        t=Trial(m,'current_200_63',0,399)
        t.sales=[dict(symbol=ETF,exit_date='2023-12-01',gain=100000,holding_days=400)]*2
        t.update_tax()
        self.assertEqual(t.tax,9375)
        self.assertAlmostEqual(sum(t.reserve(b) for b in t.books),t.tax)

    def test_future_extreme_does_not_change_cleaned_past(self):
        idx=pd.bdate_range('2020-01-01',periods=500)
        p=np.linspace(100,140,500)
        raw=pd.DataFrame(dict(open=p,high=p*1.01,low=p*.99,close=p,
                              adjclose=p,volume=np.ones(500)*1000000),index=idx)
        changed=raw.copy(); changed.iloc[350:,:5]*=100
        cfg=D.load_config()
        a=E.build_panel({'TEST.NS':clean(raw)},cfg)['TEST.NS']
        b=E.build_panel({'TEST.NS':clean(changed)},cfg)['TEST.NS']
        self.assertTrue(a.mom_score.iloc[300:350].notna().all())
        pd.testing.assert_frame_equal(a.iloc[:350],b.iloc[:350])

    def test_prefix_engine_matches_complete_engine(self):
        m=synthetic([100]*260+list(np.linspace(100,150,80)))
        short=synthetic([100]*260+list(np.linspace(100,150,80))[:40])
        a=Trial(m,'index_hold',260,339).run()
        b=Trial(short,'index_hold',260,299).run()
        self.assertEqual(a.history[:40],b.history)

    def test_dip_threshold_and_cash_budget(self):
        m=synthetic([100,89,79,69,100,100])
        t=Trial(m,'index_dip',0,5,cost_mult=0,tax=False).run()
        buys=[x for x in t.trades if x['side']=='buy']
        self.assertEqual([x['i'] for x in buys],[2,3,4])
        self.assertLessEqual(sum(x['qty']*x['price'] for x in buys),100000)
        self.assertTrue(all(x['cash']>=0 for x in t.history))


if __name__=='__main__':
    unittest.main(verbosity=2)
