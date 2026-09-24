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

from qlab import engine as E
from qlab import costs as C
from qlab import tax as TAX

_OID = [0]


def _oid():
    _OID[0] += 1
    return _OID[0]


def new_livebook(cfg: dict, name: str) -> dict:
    return {"name": name, "capital": float(cfg["starting_capital"]),
            "cash": float(cfg["starting_capital"]), "holdings": {}, "orders": [],
            "history": [], "closed_trades": [], "realized_sales": [], "realized_pnl": 0.0,
            "charges_total": 0.0, "tax_accrued": 0.0, "tax_detail": {},
            "as_of": None, "inception": None, "step_count": 0}


def total_value(state, prices):
    mv = sum(h["qty"] * prices.get(s, h.get("avg", 0)) for s, h in state["holdings"].items())
    return state["cash"] + mv


def _settle_date(date, days):
    return str((pd.Timestamp(date) + pd.tseries.offsets.BDay(days)).date())


def step(state, panel, date, cfg, regime_ok, regime_factor):
    dstr = str(pd.Timestamp(date).date())
    state["inception"] = state["inception"] or dstr
    state["step_count"] += 1
    state["risk_on"] = bool(regime_ok)
    slip = cfg.get("slippage_bps", 5) / 10000.0
    settle_days = cfg.get("settlement", {}).get("settle_days", 1)
    ccfg = cfg["costs"]; prod = "delivery"
    prices = {s: E._get(panel[s], date, "adjclose") for s in panel
              if E._get(panel[s], date, "adjclose") is not None}

    def _est_cost(value, side, sym):
        return C.order_cost(value, side, sym, prod, ccfg)

    # ---- 1. FILL yesterday's SCHEDULED orders at today's OPEN ----
    for o in state["orders"]:
        if o["status"] != "scheduled":
            continue
        e = panel.get(o["symbol"])
        op = E._get(e, date, "adj_open") if e is not None else None
        if op is None:
            continue  # market shut for it — stays scheduled
        if o["side"] == "BUY":
            fill = op * (1 + slip)
            qty = int(min(o["target_value"], state["cash"] * 0.99) // fill)
            if qty < 1:
                o["status"] = "cancelled"; continue
            gross = fill * qty; ch = _est_cost(gross, "buy", o["symbol"])
            if state["cash"] < gross + ch:
                qty = int((state["cash"] * 0.99 - ch) // fill)
                if qty < 1:
                    o["status"] = "cancelled"; continue
                gross = fill * qty; ch = _est_cost(gross, "buy", o["symbol"])
            state["cash"] = round(state["cash"] - gross - ch, 2)
            state["charges_total"] = round(state["charges_total"] + ch, 2)
            h = state["holdings"].setdefault(o["symbol"], {"qty": 0, "cost": 0.0, "avg": 0.0,
                                                           "kind": o["kind"], "stop": o.get("stop", 0.0)})
            h.setdefault("acquired", dstr)  # purchase date for the tax holding-period
            h["qty"] += qty; h["cost"] = round(h["cost"] + gross + ch, 2)
            h["avg"] = round(h["cost"] / h["qty"], 2); h["stop"] = o.get("stop", h.get("stop", 0.0))
            h["settle_date"] = _settle_date(date, settle_days)
            o.update(status="filled", fill_date=dstr, fill_price=round(fill, 2), qty=qty,
                     cost=round(ch, 2), amount=round(gross, 2), settle_date=h["settle_date"])
        else:  # SELL
            h = state["holdings"].get(o["symbol"])
            if not h or h["qty"] < 1:
                o["status"] = "cancelled"; continue
            qty = min(h["qty"], o.get("qty") or h["qty"])
            fill = op * (1 - slip); gross = fill * qty; ch = _est_cost(gross, "sell", o["symbol"])
            state["cash"] = round(state["cash"] + gross - ch, 2)
            state["charges_total"] = round(state["charges_total"] + ch, 2)
            net = gross - ch - h["avg"] * qty
            state["realized_pnl"] = round(state["realized_pnl"] + net, 2)
            state["realized_sales"].append({"symbol": o["symbol"], "exit_date": dstr, "gain": round(net, 2),
                                            "holding_days": (pd.Timestamp(dstr) - pd.Timestamp(h.get("acquired", dstr))).days})
            state["closed_trades"].append({"symbol": o["symbol"], "exit_date": dstr,
                                           "net_pnl": round(net, 2), "charges": round(ch, 2)})
            h["qty"] -= qty; h["cost"] = round(h["avg"] * h["qty"], 2)
            if h["qty"] <= 0:
                del state["holdings"][o["symbol"]]
            o.update(status="filled", fill_date=dstr, fill_price=round(fill, 2), qty=qty,
                     cost=round(ch, 2), amount=round(gross, 2), settle_date=_settle_date(date, settle_days))

    # ---- 2. SETTLE ----
    for o in state["orders"]:
        if o["status"] == "filled" and o.get("settle_date") and dstr >= o["settle_date"]:
            o["status"] = "settled"
    for h in state["holdings"].values():
        h["settled"] = bool(h.get("settle_date") and dstr >= h["settle_date"])
    # keep only recent settled orders for display
    state["orders"] = [o for o in state["orders"]
                       if o["status"] in ("scheduled", "filled") or o.get("fill_date") == dstr]

    # ---- 3. manage STOPS (resting orders — fill same day at the stop) ----
    for sym, h in list(state["holdings"].items()):
        if h["kind"] != "stock" or not h.get("stop"):
            continue
        e = panel.get(sym); low = E._get(e, date, "adj_low")
        if low is not None and low <= h["stop"]:
            fill = h["stop"] * (1 - slip); qty = h["qty"]; gross = fill * qty
            ch = _est_cost(gross, "sell", sym)
            state["cash"] = round(state["cash"] + gross - ch, 2)
            state["charges_total"] = round(state["charges_total"] + ch, 2)
            net = gross - ch - h["avg"] * qty
            state["realized_pnl"] = round(state["realized_pnl"] + net, 2)
            state["realized_sales"].append({"symbol": sym, "exit_date": dstr, "gain": round(net, 2),
                                            "holding_days": (pd.Timestamp(dstr) - pd.Timestamp(h.get("acquired", dstr))).days})
            state["closed_trades"].append({"symbol": sym, "exit_date": dstr,
                                           "net_pnl": round(net, 2), "charges": round(ch, 2)})
            state["orders"].append({"id": _oid(), "side": "SELL", "symbol": sym, "kind": "stock",
                                    "status": "filled", "fill_date": dstr, "fill_price": round(fill, 2),
                                    "qty": qty, "cost": round(ch, 2), "amount": round(gross, 2),
                                    "reason": "stop-loss hit", "settle_date": _settle_date(date, settle_days)})
            del state["holdings"][sym]

    # ---- 4. DECIDE — circuit-breaker check, then rebalance on cadence (or day 1) ----
    value_now = total_value(state, prices)
    state["peak_value"] = max(state.get("peak_value", state["capital"]), value_now)
    rk = cfg.get("risk", {}); cb = rk.get("circuit_breaker_dd", 0)
    if cb and value_now < state["peak_value"] * (1 - cb):
        state["breaker"] = True
    elif state.get("breaker") and value_now > state["peak_value"] * (1 - rk.get("reset_dd", cb)):
        state["breaker"] = False
    breaker = bool(state.get("breaker"))
    effective_on = regime_ok and not breaker

    rr = cfg["rebalance"]["long_term_rerank_days"]
    since = (state["step_count"] - 1) % rr
    state["next_rebalance_in"] = (rr - since) if since else rr
    held_stocks = {s for s, h in state["holdings"].items() if h["kind"] == "stock"}
    is_rebal = (state["step_count"] == 1) or (state["step_count"] % rr == 1) or (breaker and held_stocks)
    if is_rebal:
        state["orders"] = [o for o in state["orders"] if o["status"] != "scheduled"]  # drop stale
        sp = cfg["sleeves"]["long_term"]; K = sp["max_positions"]
        eq = value_now
        eq_weight, asset_weights = E._allocation(cfg, panel, date, regime_factor)
        ref = cfg.get("sizing_ref_vol", 0.30)
        top = E._momentum_top_set(panel, date, K, cfg) if effective_on else []
        tx = cfg.get("tax", {}); aware = tx.get("aware_exits"); buf = tx.get("ltcg_buffer_days", 30); ltd = tx.get("long_term_days", 365)
        for s in held_stocks:  # sell stocks that dropped out of the leaders
            if s in top:
                continue
            h = state["holdings"][s]
            hd = (pd.Timestamp(dstr) - pd.Timestamp(h.get("acquired", dstr))).days
            gain = (prices.get(s, h["avg"]) - h["avg"]) * h["qty"]
            if aware and not breaker and gain > 0 and (ltd - buf) <= hd <= ltd:
                continue  # tax-aware: hold a near-1-yr winner past 12mo (STCG 20% → LTCG 12.5%)
            state["orders"].append({"id": _oid(), "side": "SELL", "symbol": s, "kind": "stock",
                                    "status": "scheduled", "decided_date": dstr,
                                    "reason": "circuit-breaker de-risking" if breaker else "dropped out of top ranks"})
        for s in top:  # buy new leaders
            if s in held_stocks:
                continue
            v = E._get(panel[s], date, "vol20") or 0.30; tilt = min(1.8, max(0.4, ref / v))
            tv = (1 / K) * tilt * eq_weight * eq
            px = prices.get(s); atr = E._get(panel[s], date, "atr14")
            stop = round(px - sp["atr_stop_mult"] * atr, 1) if (px and atr) else 0.0
            state["orders"].append({"id": _oid(), "side": "BUY", "symbol": s, "kind": "stock",
                                    "status": "scheduled", "decided_date": dstr,
                                    "target_value": round(tv, 0), "stop": stop, "ref_price": round(px or 0, 1)})
        for asset, w in asset_weights.items():  # basket toward target weight
            cur = state["holdings"].get(asset, {}).get("qty", 0) * prices.get(asset, 0)
            tgt = w * eq; ap = prices.get(asset, 0)
            if w > 0 and ap > 0 and tgt - cur > 0.06 * max(tgt, 1):
                state["orders"].append({"id": _oid(), "side": "BUY", "symbol": asset, "kind": "cushion",
                                        "status": "scheduled", "decided_date": dstr,
                                        "target_value": round(tgt - cur, 0), "stop": 0.0,
                                        "ref_price": round(ap, 1)})
            elif cur - tgt > 0.06 * max(cur, 1) and cur > 0 and ap:
                q = min(state["holdings"][asset]["qty"], int((cur - tgt) // ap))
                if q >= 1:
                    state["orders"].append({"id": _oid(), "side": "SELL", "symbol": asset, "kind": "cushion",
                                            "status": "scheduled", "decided_date": dstr, "qty": q,
                                            "reason": "trim to target"})

    state["tax_accrued"], state["tax_detail"] = TAX.accrued_tax(state["realized_sales"], cfg)
    state["history"].append([dstr, round(total_value(state, prices), 2)])
    state["as_of"] = dstr
    return state
