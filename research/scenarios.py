"""Mechanism checks on explicitly invented price paths, not historical evidence."""
import json
import numpy as np
import pandas as pd

from challenge import OUT, Trial, VARIANTS, ETF
from test_challenge import synthetic


class FilterTrial(Trial):
    def decide(self,b,i):
        local=i-self.start
        if local % self.cadence:
            return
        b.orders=[]
        gate=bool(self.m.gates[200][i])
        if gate and not b.qty(ETF):
            self.order(b,i,'buy',ETF,value=max(0,b.cash-self.reserve(b)))
        elif not gate and b.qty(ETF):
            self.order(b,i,'sell',ETF,qty=b.qty(ETF))


def main():
    warmup=np.full(260,100.)
    fall=np.linspace(100,80,40)
    paths={
        'rebound_80_to_120':np.r_[fall,np.linspace(80,120,120),np.full(92,120)],
        'continued_decline_80_to_40':np.r_[fall,np.linspace(80,40,120),np.full(92,40)],
        'choppy_80_to_105':np.r_[fall,np.interp(np.arange(212),[0,35,70,105,140,175,211],[80,105,80,105,80,105,80])],
    }
    result={}
    all_curves=[]
    for scenario,path in paths.items():
        prices=np.r_[warmup,path]
        # Open of each new day equals previous close: today's signal cannot
        # capture today's close-to-close move by buying at today's close.
        m=synthetic(prices,np.r_[prices[0],prices[:-1]])
        result[scenario]={}
        for rule in ['hold','dip','200_day_daily','200_day_quarterly']:
            cls=Trial if rule in ['hold','dip'] else FilterTrial
            t=cls(m,'index_dip' if rule=='dip' else 'index_hold',260,len(prices)-1)
            if rule.startswith('200'):
                t.cadence=1 if rule.endswith('daily') else 63
            t.run()
            result[scenario][rule]=t.summary()
            for row in t.history:
                all_curves.append(dict(scenario=scenario,rule=rule,**row))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'synthetic.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    pd.DataFrame(all_curves).to_csv(OUT/'synthetic_curves.csv',index=False)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
