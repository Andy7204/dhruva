"""Realistic live paper book — models the actual Indian order lifecycle.

Unlike the backtest engine (which fills at the same day's close for speed), this
mirrors reality for the money you'd actually deploy:

  • You DECIDE after the close (the 6:30 pm run).
  • The order is SCHEDULED and fills at the NEXT session's OPEN (next-open fill).
  • Delivery settles T+1, so it takes ~1–2 trading days to truly land in your demat.
  • EVERY fill — stock or ETF (GOLDBEES/SILVERBEES/…) — pays full Groww charges.

Order statuses: scheduled → filled(settling) → held(settled). Same strategy brain
as the backtest (momentum rank + adaptive allocation + gated basket + crash filter),
just executed honestly.
"""
from __future__ import annotations

import pandas as pd
import math

from qlab import engine as E
from qlab import costs as C
from qlab import tax as TAX
from qlab import lots as LOTS


def execution_price(frame, date, field='close'):
    """Quoted prices for executable units; adjusted-only legacy fixtures remain explicit."""
    column=field if field in frame.columns else {'open':'adj_open','low':'adj_low','close':'adjclose'}[field]
    value=E._get(frame,date,column)
    if value is not None and (not math.isfinite(value) or value<=0):
        raise ValueError('Invalid executable price')
    return value


def execution_prices(panel,date):
    return {s:p for s,f in panel.items() if (p:=execution_price(f,date)) is not None}

def _oid(state):
    # Persisted counter + book namespace: independent of process restart/order date.
    used={str(o['id']) for o in state['orders']}
    seq=state.get('order_sequence',0)
    while True:
        seq+=1
        candidate=f"{state['name']}:{seq}"
        if candidate not in used:
            state['order_sequence']=seq
            return candidate


def new_livebook(cfg: dict, name: str) -> dict:
    return {"name": name, "accounting_schema":2, "capital": float(cfg["starting_capital"]),
            "cash": float(cfg["starting_capital"]), "receivables": [], "holdings": {}, "orders": [],
            "history": [], "closed_trades": [], "realized_sales": [], "realized_pnl": 0.0,
            "charges_total": 0.0, "tax_accrued": 0.0, "tax_detail": {},
            "as_of": None, "inception": None, "step_count": 0}


def total_value(state, prices):
    for symbol in state['holdings']:
        if symbol not in prices or not math.isfinite(prices[symbol]) or prices[symbol]<=0:
            raise ValueError(f'Missing/invalid valuation price: {symbol}')
    mv = sum(h["qty"] * prices[s] for s, h in state["holdings"].items())
    return state["cash"] + state.get('tax_prepaid',0.) + sum(r["amount"] for r in state.get("receivables",[])) + mv - state.get("tax_reserve",0.)


def _settle_date(date, days):
    from dhruva.calendar import settlement_date
    return settlement_date(date,days)


def _near_term_fifo_winner(inventory, qty, price, date, long_days, buffer_days):
    """Past-only exit heuristic over the taxpayer lots actually consumed by FIFO.

    Not a tax saving forecast: future prices and annual exemption usage are unknown.
    """
    left=qty
    for lot in inventory.get('lots',[]):
        used=min(left,lot['qty'])
        if used<=0: break
        held=(pd.Timestamp(date)-pd.Timestamp(lot['acquired'])).days
        basis=lot['tax_cost']/lot['qty']
        if price>basis and long_days-buffer_days<=held<=long_days:
            return True
        left=round(left-used,9)
    return False


def _deliverable_qty(holding, day):
    """Whole FIFO units available before today's settlement; no BTST credit."""
    quantity=0.
    for lot in holding.get('lots',[]):
        if lot.get('settle_date',holding.get('settle_date',day))>=day:
            break
        quantity+=lot['qty']
    return int(round(quantity,9))


def step(state, panel, date, cfg, regime_ok, regime_factor, tax_sync=None, tax_inventory=None):
    dstr = str(pd.Timestamp(date).date())
    if state.get('as_of') == dstr: return state
    if state.get('as_of') and state['as_of'] > dstr:
        raise ValueError('Cannot step a paper book backwards')
    for symbol in state['holdings']:
        frame=panel.get(symbol)
        if frame is None or any(execution_price(frame,date,c) is None for c in ('open','low','close')):
            raise ValueError(f'Missing held-symbol executable prices: {symbol}')
        previous=state.get('as_of')
        if previous and 'close' in frame and pd.Timestamp(previous) not in frame.index:
            raise ValueError(f'Missing prior raw quote for held symbol: {symbol}')
        if previous and 'close' in frame and pd.Timestamp(previous) in frame.index:
            old_quote=execution_price(frame,pd.Timestamp(previous))
            recorded=state.get('last_raw_prices',{}).get(symbol)
            if recorded is not None and not math.isclose(old_quote,recorded,rel_tol=1e-7,abs_tol=1e-6):
                raise ValueError(f'Held raw-price history revised: {symbol}; corporate-action reconciliation required')
            if state.get('price_convention')!='actual_quoted_units':
                check_dates={previous}|{lot['acquired'] for lot in state['holdings'][symbol].get('lots',[])}
                for check_date in check_dates:
                    quote=execution_price(frame,pd.Timestamp(check_date))
                    adjusted=E._get(frame,pd.Timestamp(check_date),'adjclose')
                    if quote is None or adjusted is None or not math.isclose(quote,adjusted,rel_tol=1e-7,abs_tol=1e-6):
                        raise ValueError(f'Legacy adjusted units require explicit reconciliation: {symbol}')
    settlement=_settle_date(date,cfg.get('settlement',{}).get('settle_days',1))
    for symbol,holding in state['holdings'].items():
        if not holding.get('lots'):
            raise ValueError(f'FIFO reconciliation required for {symbol}; refusing invented acquisition basis')
    state["inception"] = state["inception"] or dstr
    state["step_count"] += 1
    state["risk_on"] = bool(regime_ok)
    slip = cfg.get("slippage_bps", 5) / 10000.0
    settle_days = cfg.get("settlement", {}).get("settle_days", 1)
    ccfg = cfg["costs"]; prod = "delivery"
    prices = execution_prices(panel,date)

    def sync_tax():
        if tax_sync: tax_sync()
        else: TAX.reserve_accounts({state['name']:state},cfg)

    def available_cash():
        unpaid=max(0.,state.get('tax_reserve',0.)-state.get('tax_prepaid',0.))
        return max(0.,state['cash']-unpaid)

    def charges(value,side,sym):
        return C.order_charges(value,side,prod,C.exchange_of(sym),ccfg,sym)

    def _est_cost(value, side, sym): return charges(value,side,sym)['total']

    def record_sale(sym,qty,gross,ch,order_id):
        records=LOTS.sell(state['holdings'][sym],qty,gross,charges(gross,'sell',sym),dstr,sym,order_id)
        net=round(sum(r['economic_gain'] for r in records),2)
        if tax_inventory is not None:
            # Virtual sleeves share one owner's tax FIFO, even when the selling
            # sleeve bought more recently. Economic attribution stays per sleeve.
            records=LOTS.sell(tax_inventory[sym],qty,gross,charges(gross,'sell',sym),dstr,sym,order_id)
            for r in records: r['economic_gain']=round(net*r['qty']/qty,2)
            if not tax_inventory[sym]['qty']: del tax_inventory[sym]
        state['realized_sales'].extend(records)
        state['realized_pnl']=round(state['realized_pnl']+net,2)
        state['closed_trades'].append({'symbol':sym,'exit_date':dstr,'order_id':order_id,
                                      'net_pnl':net,'charges':round(ch,2)})
        sync_tax()
    sync_tax()

    def settle_cash(inclusive):
        pending=[]
        for receipt in state.get('receivables',[]):
            due=receipt['settle_date']<=dstr if inclusive else receipt['settle_date']<dstr
            if due: state['cash']=round(state['cash']+receipt['amount'],2)
            else: pending.append(receipt)
        state['receivables']=pending

    def sale_receivable(amount, order_id):
        # Delivery fees can exceed a tiny sale's proceeds. Reserve the deficit
        # immediately from settled cash instead of inventing a negative asset.
        amount=round(amount,2)
        if amount < 0:
            if available_cash() < -amount:
                raise ValueError('Insufficient settled cash for sale charge deficit')
            state['cash']=round(state['cash']+amount,2)
            return
        state['receivables'].append({'order_id':order_id,'amount':round(amount,2),
                                    'settle_date':settlement})

    # A delayed recovery may start after settlement. Today's payout is not
    # available at today's open: conservative cash-only delivery, no BTST/margin.
    settle_cash(False)
    # ---- 1. FILL yesterday's SCHEDULED orders at today's OPEN ----
    for o in state["orders"]:
        if o["status"] != "scheduled" or o.get("decided_date",dstr) >= dstr:
            continue
        e = panel.get(o["symbol"])
        op = execution_price(e,date,'open') if e is not None else None
        if op is None:
            continue  # market shut for it — stays scheduled
        if o["side"] == "BUY":
            fill = op * (1 + slip)
            qty = int(min(o["target_value"], available_cash() * 0.99) // fill)
            if o['kind']=='stock':
                stocks={s:h for s,h in state['holdings'].items() if h['kind']=='stock'}
                sp=cfg['sleeves']['long_term'];sectors=E._sectors()
                sec=sectors.get(o['symbol']) or o['symbol']
                if o['symbol'] not in stocks and (len(stocks)>=sp['max_positions'] or
                    sum((sectors.get(s) or s)==sec for s in stocks)>=cfg.get('selection',{}).get('max_per_sector',999)):
                    o.update(status='cancelled',cancelled_date=dstr,reason='Position/sector count limit');continue
                open_prices={s:execution_price(panel[s],date,'open') for s in state['holdings']}
                nav_open=total_value(state,open_prices)
                held_qty=stocks.get(o['symbol'],{}).get('qty',0)
                cap=sp['max_pos_weight']
                qty=min(qty,max(0,int((cap*nav_open-held_qty*op)//fill)))
                while qty and (held_qty+qty)*op>cap*(nav_open-_est_cost(qty*fill,'buy',o['symbol'])-qty*(fill-op)):
                    qty-=1
            if qty < 1:
                o.update(status="cancelled",cancelled_date=dstr,reason="Insufficient cash or quantity"); continue
            gross = fill * qty; ch = _est_cost(gross, "buy", o["symbol"])
            if available_cash() < gross + ch:
                qty = int((available_cash() * 0.99 - ch) // fill)
                if qty < 1:
                    o.update(status="cancelled",cancelled_date=dstr,reason="Insufficient cash or quantity"); continue
                gross = fill * qty; ch = _est_cost(gross, "buy", o["symbol"])
            state["cash"] = round(state["cash"] - gross - ch, 2)
            state["charges_total"] = round(state["charges_total"] + ch, 2)
            h = state["holdings"].setdefault(o["symbol"], {"qty": 0, "cost": 0.0, "avg": 0.0,
                                                           "kind": o["kind"], "stop": o.get("stop", 0.0)})
            for lot in h.get('lots',[]):
                lot.setdefault('settle_date',h.get('settle_date',dstr))
            LOTS.buy(h,qty,gross,charges(gross,'buy',o['symbol']),dstr,o['id'])
            next(lot for lot in h['lots'] if lot['id']==o['id'])['settle_date']=settlement
            h.setdefault('acquired_step',state['step_count'])
            if tax_inventory is not None:
                LOTS.buy(tax_inventory.setdefault(o['symbol'],{}),qty,gross,
                         charges(gross,'buy',o['symbol']),dstr,o['id'])
            h['stop']=o.get('stop',h.get('stop',0.))
            h['settle_date']=settlement
            o.update(status="filled", fill_date=dstr, fill_price=round(fill, 2), qty=qty,
                     cost=round(ch, 2), amount=round(gross, 2), settle_date=h["settle_date"])
        else:  # SELL
            h = state["holdings"].get(o["symbol"])
            if not h or h["qty"] < 1:
                o.update(status="cancelled",cancelled_date=dstr,reason="Insufficient cash or quantity"); continue
            deliverable=_deliverable_qty(h,dstr)
            requested=int(min(h['qty'],o.get('qty') or h['qty']))
            if deliverable < requested:
                o['pending_reason']='Awaiting delivery settlement'; continue
            qty = int(min(h["qty"], o.get("qty") or h["qty"]))
            if qty < 1:
                o.update(status='cancelled', cancelled_date=dstr,
                         reason='No whole exchange units requested')
                continue
            fill = op * (1 - slip); gross = fill * qty; ch = _est_cost(gross, "sell", o["symbol"])
            sale_receivable(gross-ch,o["id"])
            state["charges_total"] = round(state["charges_total"] + ch, 2)
            record_sale(o['symbol'],qty,gross,ch,o['id'])
            if h["qty"] <= 0:
                del state["holdings"][o["symbol"]]
            o.update(status="filled", fill_date=dstr, fill_price=round(fill, 2), qty=qty,
                     cost=round(ch, 2), amount=round(gross, 2), settle_date=settlement)

    # ---- 2. SETTLE ----
    for o in state["orders"]:
        if o["status"] == "filled" and o.get("settle_date") and dstr >= o["settle_date"]:
            o["status"] = "settled"
    for h in state["holdings"].values():
        h["settled"] = bool(h.get("settle_date") and dstr >= h["settle_date"])
    # The engine retains every order. Display filtering belongs in the UI only.

    # ---- 3. manage STOPS (resting orders — fill same day at the stop) ----
    for sym, h in list(state["holdings"].items()):
        if h["kind"] != "stock" or not h.get("stop") or not _deliverable_qty(h,dstr):
            continue
        e = panel.get(sym); low = execution_price(e,date,'low')
        if low is not None and low <= h["stop"]:
            fill = min(h["stop"], execution_price(e,date,'open')) * (1 - slip); qty = _deliverable_qty(h,dstr)
            if not qty: continue  # fractional fund allotments cannot trade on exchange
            gross = fill * qty
            ch = _est_cost(gross, "sell", sym)
            stop_id=_oid(state)
            sale_receivable(gross-ch,stop_id)
            state["charges_total"] = round(state["charges_total"] + ch, 2)
            record_sale(sym,qty,gross,ch,stop_id)
            state["orders"].append({"id": stop_id, "side": "SELL", "symbol": sym, "kind": "stock",
                                    "status": "filled", "fill_date": dstr, "fill_price": round(fill, 2),
                                    "qty": qty, "cost": round(ch, 2), "amount": round(gross, 2),
                                    "reason": "stop-loss hit", "settle_date": settlement})
            if h['qty']<=0: del state["holdings"][sym]

    settle_cash(True)

    # ---- 4. DECIDE — circuit-breaker check, then rebalance on cadence (or day 1) ----
    value_now = total_value(state, prices)
    state["peak_value"] = max(state.get("peak_value", state["capital"]), value_now)
    rk = cfg.get("risk", {}); cb = rk.get("circuit_breaker_dd", 0)
    reset_now=False
    if cb and value_now < state["peak_value"] * (1 - cb) and not state.get('breaker'):
        state["breaker"] = True
        state['breaker_trigger_step']=state['step_count']
    if state.get('breaker'):
        state.setdefault('breaker_trigger_step',state['step_count'])
        recovered=value_now>state['peak_value']*(1-rk.get('reset_dd',cb))
        cooldown=state['step_count']-state['breaker_trigger_step']>=rk.get('cooldown_sessions',63)
        if recovered or (cooldown and regime_ok):
            state['breaker']=False;reset_now=True;state['peak_value']=value_now
            state['breaker_reset_reason']='Recovered NAV' if recovered else 'Cooldown completed with market trend on'
    breaker = bool(state.get("breaker"))
    effective_on = regime_ok and not breaker

    rr = cfg["rebalance"]["long_term_rerank_days"]
    since = (state["step_count"] - 1) % rr
    state["next_rebalance_in"] = (rr - since) if since else rr
    held_stocks = {s for s, h in state["holdings"].items() if h["kind"] == "stock"}
    is_rebal = (state["step_count"] == 1) or (state["step_count"] % rr == 1) or (breaker and held_stocks) or reset_now
    if is_rebal:
        for order in state['orders']:
            if order['status']=='scheduled':
                order.update(status='cancelled',cancelled_date=dstr,reason='Superseded by rebalance')
        sp = cfg["sleeves"]["long_term"]; K = sp["max_positions"]
        eq = value_now
        eq_weight, asset_weights = E._allocation(cfg, panel, date, regime_factor)
        ref = cfg.get("sizing_ref_vol", 0.30)
        top = E._momentum_top_set(panel, date, K, cfg) if effective_on else []
        tx = cfg.get("tax", {}); aware = tx.get("aware_exits"); buf = tx.get("ltcg_buffer_days", 30); ltd = tx.get("long_term_days", 365)
        for s in sorted(held_stocks):  # sell stocks that dropped out of the leaders
            if s in top:
                continue
            h = state["holdings"][s]
            minimum=cfg.get('entry_filters',{}).get('min_hold_days',{}).get('long_term',0)
            if not breaker and state['step_count']-h.get('acquired_step',0)<minimum: continue
            fifo = tax_inventory[s] if tax_inventory is not None else h
            if aware and not breaker and _near_term_fifo_winner(
                    fifo, int(h['qty']), prices[s], dstr, ltd, buf):
                continue  # tax-aware: hold a near-1-yr winner past 12mo (STCG 20% → LTCG 12.5%)
            state["orders"].append({"id": _oid(state), "side": "SELL", "symbol": s, "kind": "stock",
                                    "status": "scheduled", "decided_date": dstr,
                                    "reason": "circuit-breaker de-risking" if breaker else "dropped out of top ranks"})
        for s in top:  # buy new leaders
            if s in held_stocks:
                continue
            v = E._get(panel[s], date, "vol20") or 0.30; tilt = min(1.8, max(0.4, ref / v))
            tv = min((1 / K) * tilt * eq_weight * eq,sp['max_pos_weight']*eq)
            px = prices.get(s); atr = E._get(panel[s], date, "atr14")
            if not px or not atr: continue
            adjusted=E._get(panel[s],date,'adjclose')
            if adjusted: atr*=px/adjusted  # ATR signal units -> quoted execution units.
            estimated_fees=_est_cost(tv,'buy',s)+_est_cost(tv,'sell',s)
            distance=sp['atr_stop_mult']*atr/px
            if tv<=0 or distance<cfg.get('entry_filters',{}).get('min_edge_to_cost',0)*estimated_fees/tv: continue
            stop = round(px - sp["atr_stop_mult"] * atr, 1) if (px and atr) else 0.0
            state["orders"].append({"id": _oid(state), "side": "BUY", "symbol": s, "kind": "stock",
                                    "status": "scheduled", "decided_date": dstr,
                                    "target_value": round(tv, 0), "stop": stop, "ref_price": round(px or 0, 1)})
        for asset, w in asset_weights.items():  # basket toward target weight
            cur = state["holdings"].get(asset, {}).get("qty", 0) * prices.get(asset, 0)
            tgt = w * eq; ap = prices.get(asset, 0)
            if w > 0 and ap > 0 and tgt - cur > 0.06 * max(tgt, 1):
                state["orders"].append({"id": _oid(state), "side": "BUY", "symbol": asset, "kind": "cushion",
                                        "status": "scheduled", "decided_date": dstr,
                                        "target_value": round(tgt - cur, 0), "stop": 0.0,
                                        "ref_price": round(ap, 1)})
            elif cur - tgt > 0.06 * max(cur, 1) and cur > 0 and ap:
                q = min(state["holdings"][asset]["qty"], int((cur - tgt) // ap))
                if q >= 1:
                    state["orders"].append({"id": _oid(state), "side": "SELL", "symbol": asset, "kind": "cushion",
                                            "status": "scheduled", "decided_date": dstr, "qty": q,
                                            "reason": "trim to target"})

    sync_tax()
    state["history"].append([dstr, round(total_value(state, prices), 2)])
    state["as_of"] = dstr
    raw_units=all('close' in panel[s] for s in state['holdings'])
    state['price_convention']='actual_quoted_units' if raw_units else 'legacy_adjusted_fixture_units'
    state['last_raw_prices']={s:prices[s] for s in state['holdings'] if 'close' in panel[s]}
    return state
