"""Fixed-rule, offline challenge study. Never writes production data or paper books.

Run with Python 3.12+: python research/challenge.py
Research assumptions and departures from the deployed execution engine are in
research/PROTOCOL.md. Uses only supplied cache files; no network fetches.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qlab import costs as C, data as D, engine as E, indicators as I, tax as T

OUT = ROOT / 'research' / 'results'
ETF = 'NIFTYBEES.NS'
VARIANTS = {
    'current_200_63': (200, 63, False, 'momentum'),
    'faster_100_63': (100, 63, False, 'momentum'),
    'faster_50_63': (50, 63, False, 'momentum'),
    'monthly_200_21': (200, 21, False, 'momentum'),
    'crossing_200_63': (200, 63, True, 'momentum'),
    'no_market_gate_63': (0, 63, False, 'momentum'),
    'core_plus_dip': (200, 63, False, 'dip'),
    'core_plus_index': (200, 63, False, 'hold'),
    'index_hold': (0, 1, False, 'all_hold'),
    'index_dip': (0, 1, False, 'all_dip'),
}


def clean(df):
    """Contemporaneous validity checks only; never a centered/outlier filter."""
    df = df.sort_index().loc[lambda x: ~x.index.duplicated(keep='last')]
    valid = (df[['open', 'high', 'low', 'close', 'adjclose']] > 0).all(axis=1)
    valid &= df.high >= df[['open', 'close', 'low']].max(axis=1)
    valid &= df.low <= df[['open', 'close', 'high']].min(axis=1)
    return df.loc[valid].copy()


class Market:
    def __init__(self, cfg):
        self.cfg = cfg
        symbols = list(dict.fromkeys(cfg['universe'] + [ETF, '^NSEI']))
        self.raw, self.audit = {}, {}
        for s in symbols:
            p = ROOT / 'data/cache' / (D._safe_name(s) + '.csv')
            if not p.exists():
                self.audit[s] = {'missing': True}
                continue
            raw = pd.read_csv(p, index_col='date', parse_dates=['date'])
            frame = clean(raw)
            self.raw[s] = frame
            self.audit[s] = {'rows': len(frame), 'rejected': len(raw)-len(frame),
                'first': str(frame.index.min().date()), 'last': str(frame.index.max().date()),
                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        # Ignore a possibly partial current trading session and align the ETF baseline.
        end = min(self.raw[ETF].index.max(), self.raw['^NSEI'].index.max())
        self.raw = {s: f.loc[:end] for s, f in self.raw.items()}
        self.panel = E.build_panel({s:f for s,f in self.raw.items() if s != '^NSEI'}, cfg)
        self.bench = I.enrich(self.raw['^NSEI'])
        self.cal = self.bench.index
        self.symbols = list(self.panel)
        self.cols = {}
        for col in ['adjclose','adj_open','adj_low','mom_score','turnover','vol20','sma200']:
            self.cols[col] = pd.DataFrame({s:e[col] for s,e in self.panel.items()}).reindex(self.cal)
        # Correct ATR price units: indicators.enrich computes ATR from raw OHLC.
        self.cols['atr14'] = pd.DataFrame({s:I.atr(pd.DataFrame({
            'high':e.adj_high,'low':e.adj_low,'close':e.adjclose}),14)
            for s,e in self.panel.items()}).reindex(self.cal)
        self.marks = self.cols['adjclose'].ffill()
        self.factor = E.regime_factor_series(cfg, self.bench).to_numpy()
        self.gates = {n:(self.bench.adjclose > self.bench.adjclose.rolling(n).mean()).to_numpy()
                      for n in [50,100,200]}
        self.gates[0] = np.ones(len(self.cal), dtype=bool)
        self.stock_set = set(cfg['universe']) - set(cfg['defensive_basket']) - {ETF}
        self.n100 = set((ROOT/'data/nifty100.txt').read_text().split())
        self.rank_cache = {}

    def px(self, s, i, col='adjclose'):
        if s not in self.cols[col]:
            return None
        v = self.cols[col].at[self.cal[i], s]
        return float(v) if pd.notna(v) and np.isfinite(v) else None

    def mark(self, s, i):
        v = self.marks.at[self.cal[i], s]
        assert np.isfinite(v), (s, i)
        return float(v)

    def top(self, i, universe):
        key = i, universe
        if key in self.rank_cache:
            return self.rank_cache[key]
        allowed = self.stock_set if universe == '500' else self.stock_set & self.n100
        score = self.cols['mom_score'].iloc[i].dropna()
        turn = self.cols['turnover'].iloc[i]
        ranked = sorted([(float(v),s) for s,v in score.items()
                         if s in allowed and turn[s] >= self.cfg['selection']['min_turnover']],reverse=True)
        chosen, sectors = [], {}
        for _,s in ranked:
            sec = E._sectors().get(s,s)
            if sectors.get(sec,0) >= self.cfg['selection']['max_per_sector']:
                continue
            chosen.append(s); sectors[sec] = sectors.get(sec,0)+1
            if len(chosen) == self.cfg['sleeves']['long_term']['max_positions']:
                break
        self.rank_cache[key] = chosen
        return chosen


@dataclass
class Book:
    capital: float
    mode: str
    balanced: bool = False
    cash: float = field(init=False)
    lots: dict = field(default_factory=dict)
    stop: dict = field(default_factory=dict)
    receivables: list = field(default_factory=list)
    orders: list = field(default_factory=list)
    peak: float = field(init=False)
    breaker: bool = False
    anchor: float | None = None
    dip_stage: int = 0
    cycle_budget: float = 0
    wait_empty: bool = False
    invested_once: bool = False
    last_gate: bool | None = None

    def __post_init__(self):
        self.cash = self.peak = self.capital

    def qty(self,s):
        return sum(x['qty'] for x in self.lots.get(s,[]))

    def value(self,m,i):
        return self.cash + sum(v for _,v in self.receivables) + sum(
            self.qty(s)*m.mark(s,i) for s in self.lots)


class Trial:
    def __init__(self,m,name,start,end,universe='500',phase=0,cost_mult=1,tax=True):
        self.m,self.name,self.start,self.end = m,name,start,end
        self.ma,self.cadence,self.cross,self.sat = VARIANTS[name]
        self.universe,self.phase,self.cost_mult,self.tax_on = universe,phase,cost_mult,tax
        if self.sat.startswith('all_'):
            self.books = [Book(100000,self.sat[4:])]
        else:
            self.books = [Book(70000,'momentum',True),Book(30000,self.sat)]
        self.sales,self.trades,self.history = [],[],[]
        self.tax,self.fees,self.slippage = 0.,0.,0.
        self.scheduled,self.filled = 0,0
        self.gap_stops = 0

    def fee(self,gross,side,s):
        return self.cost_mult*C.order_cost(gross,side,s,'delivery',self.m.cfg['costs'])

    def reserve(self,b):
        return self.tax*b.capital/100000

    def update_tax(self):
        self.tax = T.accrued_tax(self.sales,self.m.cfg)[0] if self.tax_on else 0.

    def buy(self,b,s,budget,base,i,stop=0):
        price = base*(1+self.m.cfg['slippage_bps']/10000*self.cost_mult)
        available = max(0,b.cash-self.reserve(b))
        qty = int(min(budget,available*.99)//price)
        while qty > 0 and qty*price+self.fee(qty*price,'buy',s)>available:
            qty -= 1
        if qty <= 0:
            return
        fee = self.fee(qty*price,'buy',s)
        b.cash -= qty*price+fee
        b.lots.setdefault(s,[]).append({'qty':qty,'basis':price+fee/qty,'i':i})
        b.stop[s] = stop
        self.fees += fee; self.slippage += qty*(price-base)
        self.trades.append({'i':i,'side':'buy','s':s,'qty':qty,'price':price,'fee':fee})
        self.filled += 1

    def sell(self,b,s,qty,base,i,reason='scheduled',terminal=False):
        qty = min(qty,b.qty(s))
        if qty <= 0:
            return
        price = base*(1-self.m.cfg['slippage_bps']/10000*self.cost_mult)
        fee = self.fee(qty*price,'sell',s)
        left = qty
        for lot in b.lots[s]:
            take = min(left,lot['qty'])
            if take:
                self.sales.append({'symbol':s,'exit_date':str(self.m.cal[i].date()),
                    'gain':take*(price-lot['basis'])-fee*take/qty,
                    'holding_days':(self.m.cal[i]-self.m.cal[lot['i']]).days})
                lot['qty'] -= take; left -= take
        b.lots[s] = [x for x in b.lots[s] if x['qty']]
        if not b.lots[s]:
            del b.lots[s]; b.stop.pop(s,None)
        # Sale proceeds are an asset immediately, but spendable next benchmark session.
        b.receivables.append((i+1,qty*price-fee))
        self.fees += fee; self.slippage += qty*(base-price)
        self.update_tax()
        self.trades.append({'i':i,'side':'sell','s':s,'qty':qty,'price':price,'fee':fee,
                            'reason':reason,'terminal':terminal})
        self.filled += 1

    def order(self,b,i,side,s,value=0,qty=0,stop=0):
        b.orders.append(dict(decided=i,side=side,s=s,value=value,qty=qty,stop=stop))
        self.scheduled += 1

    def decide(self,b,i):
        cfg = self.m.cfg
        if b.mode == 'hold':
            if not b.invested_once:
                self.order(b,i,'buy',ETF,value=max(0,b.cash-self.reserve(b)))
                b.invested_once = True
            return
        if b.mode == 'dip':
            if b.wait_empty:
                if b.qty(ETF) or b.orders:
                    return
                b.wait_empty=False; b.anchor=None; b.dip_stage=0
            px = float(self.m.bench.adjclose.iloc[i])
            if b.anchor is None:
                peak = float(self.m.bench.adjclose.iloc[:i+1].max())
                if px <= peak*.90:
                    b.anchor=peak; b.cycle_budget=max(0,b.cash-self.reserve(b))
            if b.anchor is not None:
                if px >= b.anchor and b.qty(ETF):
                    self.order(b,i,'sell',ETF,qty=b.qty(ETF)); b.wait_empty=True
                else:
                    stage = sum(px <= b.anchor*(1-d) for d in [.10,.20,.30])
                    if stage > b.dip_stage:
                        self.order(b,i,'buy',ETF,value=(stage-b.dip_stage)*b.cycle_budget/3)
                        b.dip_stage=stage
            return
        gate = bool(self.m.gates[self.ma][i])
        nav = b.value(self.m,i)-self.reserve(b)
        b.peak=max(b.peak,nav)
        if nav < b.peak*(1-cfg['risk']['circuit_breaker_dd']):
            b.breaker=True
        elif b.breaker and nav > b.peak*(1-cfg['risk']['reset_dd']):
            b.breaker=False
        stocks = set(b.lots)&self.m.stock_set
        local = i-self.start
        periodic = local == 0 or (local-self.phase)%self.cadence == 0
        crossing = self.cross and b.last_gate is not None and gate != b.last_gate
        b.last_gate = gate
        if not (periodic or crossing or (b.breaker and stocks)):
            return
        b.orders=[]
        top = self.m.top(i,self.universe) if gate and not b.breaker else []
        for s in sorted(stocks):
            if s in top:
                continue
            lot = b.lots[s][0]
            age=(self.m.cal[i]-self.m.cal[lot['i']]).days
            gain=sum(x['qty']*(self.m.mark(s,i)-x['basis']) for x in b.lots[s])
            tx=cfg['tax']
            if tx['aware_exits'] and not b.breaker and gain>0 and tx['long_term_days']-tx['ltcg_buffer_days'] <= age <= tx['long_term_days']:
                continue
            self.order(b,i,'sell',s,qty=b.qty(s))
        ew = cfg['allocation']['equity_min']+(cfg['allocation']['equity_max']-cfg['allocation']['equity_min'])*self.m.factor[i] if b.balanced else 1
        for s in top:
            if b.qty(s):
                continue
            vol=self.m.px(s,i,'vol20') or .3
            tilt=min(1.8,max(.4,cfg['sizing_ref_vol']/vol))
            px=self.m.px(s,i); atr=self.m.px(s,i,'atr14')
            stop=max(0,px-cfg['sleeves']['long_term']['atr_stop_mult']*atr) if px and atr else 0
            self.order(b,i,'buy',s,value=tilt*ew*nav/cfg['sleeves']['long_term']['max_positions'],stop=stop)
        if b.balanced:
            basket=cfg['defensive_basket']; total=sum(basket.values())
            for s,w in basket.items():
                px=self.m.px(s,i)
                if px is None:
                    continue
                target=(1-ew)*w/total*nav
                ma=self.m.px(s,i,'sma200')
                if s != cfg['allocation']['cash_asset'] and ma and px<=ma:
                    target=0
                cur=b.qty(s)*px
                if target-cur>.06*max(target,1):
                    self.order(b,i,'buy',s,value=target-cur)
                elif cur-target>.06*max(cur,1) and cur>0:
                    self.order(b,i,'sell',s,qty=min(b.qty(s),int((cur-target)//px)))

    def run(self):
        for i in range(self.start,self.end+1):
            for b in self.books:
                b.cash+=sum(v for due,v in b.receivables if due<=i)
                b.receivables=[(due,v) for due,v in b.receivables if due>i]
                pending=[]
                for o in b.orders:
                    assert o['decided']<i, 'Look-ahead: same-session scheduled fill'
                    px=self.m.px(o['s'],i,'adj_open')
                    if px is None:
                        pending.append(o); continue
                    if o['side']=='buy':
                        self.buy(b,o['s'],o['value'],px,i,o['stop'])
                    else:
                        self.sell(b,o['s'],o['qty'],px,i)
                b.orders=pending
                for s,stop in list(b.stop.items()):
                    low=self.m.px(s,i,'adj_low'); op=self.m.px(s,i,'adj_open')
                    if stop and low is not None and op is not None and low<=stop:
                        self.gap_stops+=int(op<stop)
                        self.sell(b,s,b.qty(s),min(op,stop),i,'stop')
                assert b.cash>=-1e-6, 'Negative cash / leverage'
            # Tax exemption and loss buckets are shared across the two books.
            self.update_tax()
            for b in self.books:
                if i<self.end:
                    self.decide(b,i)
            gross=sum(b.value(self.m,i) for b in self.books)
            nav=gross-self.tax
            cash=sum(b.cash+sum(v for _,v in b.receivables) for b in self.books)-self.tax
            equity=sum(b.qty(s)*self.m.mark(s,i) for b in self.books for s in b.lots
                       if s in self.m.stock_set or s==ETF)
            self.history.append(dict(date=str(self.m.cal[i].date()),nav=nav,cash=cash,
                                     equity=equity,tax=self.tax))
        self.pre_terminal=self.history[-1]['nav']
        self.pre_fees=self.fees
        self.pre_tax=self.tax
        for b in self.books:
            for s in list(b.lots):
                self.sell(b,s,b.qty(s),self.m.mark(s,self.end),self.end,'terminal valuation',True)
        self.terminal=sum(b.value(self.m,self.end) for b in self.books)-self.tax
        return self

    def summary(self):
        df=pd.DataFrame(self.history).set_index('date')
        eq=df.nav; daily=eq.pct_change().fillna(0)
        days=(self.m.cal[self.end]-self.m.cal[self.start]).days
        dd=(eq/eq.cummax()-1).min()*100
        terminal_dd=min(dd,(self.terminal/eq.cummax().iloc[-1]-1)*100)
        yr={str(y):round((np.prod(1+g)-1)*100,3) for y,g in daily.groupby(pd.to_datetime(daily.index).year)}
        return {'return_pct':round((self.terminal/100000-1)*100,3),
                'cagr_pct':round(((self.terminal/100000)**(365.25/days)-1)*100,3),
                'max_drawdown_pct':round(terminal_dd,3),
                'sharpe_zero_rf':round(float(daily.mean()/daily.std()*np.sqrt(252)),3) if daily.std()>0 else None,
                'fees_rupees':round(self.fees,2),'slippage_rupees':round(self.slippage,2),
                'tax_rupees':round(self.tax,2),'nav_before_liquidation':round(self.pre_terminal,2),
                'liquidation_nav':round(self.terminal,2),
                'cash_pct_average':round(float((df.cash/eq).mean()*100),2),
                'equity_pct_average':round(float((df.equity/eq).mean()*100),2),
                'trades':len(self.trades),'gap_stops':self.gap_stops,'year_returns_marked':yr,
                'end':str(self.m.cal[self.end].date()),'start':str(self.m.cal[self.start].date())}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=D.load_config()
    m=Market(cfg)
    start=260; end=len(m.cal)-1
    assert end-start>500, 'Insufficient common history'
    meta={'window':[str(m.cal[start].date()),str(m.cal[end].date())],
          'sessions':end-start+1,'data_audit':m.audit,'variants':VARIANTS,
          'config_sha256':hashlib.sha256((ROOT/'config.json').read_bytes()).hexdigest(),
          'protocol_sha256':hashlib.sha256((ROOT/'research/PROTOCOL.md').read_bytes()).hexdigest()}
    (OUT/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    results={}; curves={}; trials={}
    for universe in ['500','100']:
        for name in VARIANTS:
            print('Full window',universe,name,flush=True)
            t=Trial(m,name,start,end,universe).run()
            results[f'{universe}/{name}']=t.summary()
            if universe=='500':
                curves[name]=pd.DataFrame(t.history).set_index('date').nav
                trials[name]=t
                pd.DataFrame(t.trades).to_csv(OUT/f'trades_{name}.csv',index=False)
    # Fixed final-year temporal check, not a genuinely untouched holdout: original
    # strategy development already saw this supplied period.
    temporal={name:Trial(m,name,end-251,end).run().summary() for name in VARIANTS}
    phases={str(p):{name:Trial(m,name,start,end,phase=p).run().summary()
        for name in ['current_200_63','monthly_200_21','crossing_200_63','core_plus_dip']}
        for p in [21,42]}
    friction={label:{name:Trial(m,name,start,end,cost_mult=cm,tax=tax).run().summary()
        for name in ['current_200_63','crossing_200_63','core_plus_dip','index_hold','index_dip']}
        for label,cm,tax in [('no_friction',0,False),('costs_no_tax',1,False),('double_costs',2,True)]}
    curve=pd.DataFrame(curves)
    rolling=(curve/curve.shift(252)-1)*100
    rolling_summary={name:{'min':round(float(rolling[name].min()),2),
        'median':round(float(rolling[name].median()),2),
        'max':round(float(rolling[name].max()),2),
        'beats_current_pct':round(float((rolling[name].dropna()>rolling.current_200_63.dropna()).mean()*100),2)}
        for name in VARIANTS}
    crossings=[]
    gate=m.gates[200]
    for i in range(start+1,end):
        if gate[i] and not gate[i-1]:
            nxt=start+math.ceil((i-start)/63)*63
            j=min(nxt,end)
            crossings.append({'crossing_date':str(m.cal[i].date()),'wait_sessions':nxt-i,
                'next_review_in_window':nxt<=end,'nifty_move_to_review_pct':round(float((m.bench.adjclose.iloc[j]/m.bench.adjclose.iloc[i]-1)*100),3),
                'risk_on_at_review':bool(gate[j])})
    out={'full':results,'final_year_fresh_start':temporal,'rebalance_phase':phases,
         'friction':friction,'rolling_252_sessions':rolling_summary,'crossings':crossings}
    (OUT/'results.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    curve.to_csv(OUT/'curves.csv')
    pd.DataFrame({k:v for k,v in results.items() if k.startswith('500/')}).T.to_csv(OUT/'scorecard.csv')
    print(json.dumps({k:v for k,v in results.items() if k.startswith('500/')},indent=2),flush=True)


if __name__=='__main__':
    main()
