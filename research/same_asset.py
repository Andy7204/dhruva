"""Supplemental controls: identical NIFTYBEES asset, different market timing.

Added after the main fixed matrix to separate timing from stock selection.
No parameter optimization; same three moving averages and two review cadences.
"""
import json
import pandas as pd
from challenge import D, Market, Trial, OUT, ETF
from scenarios import FilterTrial


class ETFGateTrial(FilterTrial):
    def decide(self,b,i):
        if (i-self.start)%self.cadence:
            return
        b.orders=[]
        gate=bool(self.m.gates[self.ma][i])
        if gate and not b.qty(ETF):
            self.order(b,i,'buy',ETF,value=max(0,b.cash-self.reserve(b)))
        elif not gate and b.qty(ETF):
            self.order(b,i,'sell',ETF,qty=b.qty(ETF))


def main():
    m=Market(D.load_config()); end=len(m.cal)-1
    results={}; curves={}
    for window,start in [('full',260),('final_year',end-251)]:
        results[window]={}
        for ma,cadence in [(200,63),(200,1),(100,63),(50,63)]:
            t=ETFGateTrial(m,'index_hold',start,end)
            t.ma=ma; t.cadence=cadence
            t.run(); name=f'ETF_{ma}_{cadence}'
            results[window][name]=t.summary()
            if window=='full':
                curves[name]=pd.DataFrame(t.history).set_index('date').nav
    (OUT/'same_asset.json').write_text(json.dumps(results,indent=2))
    pd.DataFrame(curves).to_csv(OUT/'same_asset_curves.csv')
    print(json.dumps(results,indent=2))


if __name__=='__main__': main()
