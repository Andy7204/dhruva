"""Daily call — turn the strategy's state into a clear, plain decision.

Produces, for the latest close: whether the market is risk-on or risk-off, and
either a 'stay in cash' call or a concrete list of BUY / HOLD / SELL actions with
size, stop-loss, rupees-at-risk, and an illustrative win-case.

RESEARCH OUTPUT, NOT ADVICE. These are the mechanical outputs of the backtested
rules — no fixed profit target exists (momentum rides the trend until an exit
rule fires); 'win case' is an illustration from the strategy's own average winner.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qlab import engine as E


def _avg_win_loss_pct(closed):
    wins = [t["net_pnl_pct"] for t in closed if t.get("net_pnl", 0) > 0]
    losses = [t["net_pnl_pct"] for t in closed if t.get("net_pnl", 0) <= 0]
    aw = float(np.mean(wins)) if wins else 15.0
    al = float(np.mean(losses)) if losses else -8.0
    return round(aw, 1), round(al, 1)


def todays_call(cfg: dict, panel: dict, pf: dict, bench_e: pd.DataFrame) -> dict:
    date = E.trading_calendar(panel)[-1]
    ma = cfg["regime"]["ma"]
    from qlab import indicators as I
    bc = bench_e["adjclose"]
    nifty = float(bc.get(date, bc.dropna().iloc[-1]))          # fall back if index lags
    ma_ser = I.sma(bc, ma).dropna()
    nifty_ma = float(ma_ser.get(date, ma_ser.iloc[-1])) if len(ma_ser) else nifty
    risk_on = nifty > nifty_ma

    sp = cfg["sleeves"]["long_term"]
    K = sp["max_positions"]
    st = pf["sleeves"]["long_term"]
    prices_all = E._prices_at(panel, date)
    eq = E.sleeve_equity(st, prices_all)
    rf_series = E.regime_factor_series(cfg, bench_e)
    rf = 1.0 if rf_series is None else float(rf_series.get(date, 1.0))
    eq_weight, asset_weights = E._allocation(cfg, panel, date, rf)
    eq_names = eq * eq_weight  # equity budget (rest is the diversifier basket / cash)
    ref = cfg.get("sizing_ref_vol", 0.30)
    aw, al = _avg_win_loss_pct(pf.get("closed_trades", []))
    sectors = E._sectors()
    target = E._momentum_top_set(panel, date, K, cfg)
    held = set(st["positions"].keys())

    actions = []
    defensive_rows = []

    # SELLs / HOLDs on current holdings
    for sym in held:
        e = panel.get(sym)
        pos = st["positions"][sym]
        px = E._get(e, date, "adjclose") if e is not None else None
        if px is None:
            px = pos["avg_price"]  # no quote on this exact date — fall back to entry
        upnl = (px - pos["avg_price"]) * pos["qty"]
        if pos.get("strategy") == "defensive":  # gold/silver/InvIT/cash — always hold, just rebalanced
            defensive_rows.append({"symbol": sym.replace(".NS", ""), "price": round(px, 1),
                                   "value": round(pos["qty"] * px, 0), "unrealized": round(upnl, 0)})
            continue
        trend_ok = (E._get(e, date, "trend_long") == 1.0) if e is not None else False
        if not trend_ok:
            reason = "trend broken (below 200-day line)"
            action = "SELL"
        elif sym not in target:
            reason = "dropped out of the top ranks — sell at next rebalance"
            action = "TRIM/WATCH"
        else:
            reason = "still a leader — keep holding"
            action = "HOLD"
        actions.append({"action": action, "symbol": sym.replace(".NS", ""),
                        "sector": sectors.get(sym, "?"), "price": round(px, 1),
                        "qty": pos["qty"], "unrealized": round(upnl, 0),
                        "stop": pos["stop"], "reason": reason})

    # BUYs (only when risk-on) — mirror the engine's sizing: slippage, caps, running cash
    buys = []
    if risk_on:
        import math
        slip = cfg.get("slippage_bps", 5) / 10000.0
        avail = st["cash"]  # decremented as we allocate, like the engine
        for sym in target:
            if sym in held:
                continue
            e = panel[sym]
            px = E._get(e, date, "adjclose"); atr = E._get(e, date, "atr14")
            vol = E._get(e, date, "vol20") or 0.30
            if not px or not atr:
                continue
            tilt = min(1.8, max(0.4, ref / vol)) if vol > 0 else 1.0
            fill = px * (1 + slip)
            qty_target = (1 / K) * tilt * eq_names / fill
            qty_cap = (sp["max_pos_weight"] * eq) / px
            qty_cash = (avail * 0.98) / fill
            qty = int(math.floor(min(qty_target, qty_cap, qty_cash)))
            if qty < 1:
                continue
            invest = qty * fill
            avail -= invest
            stop = fill - sp["atr_stop_mult"] * atr
            px = fill  # report the realistic fill price
            risk = qty * (px - stop)
            buys.append({"action": "BUY", "symbol": sym.replace(".NS", ""),
                         "sector": sectors.get(sym, "?"), "price": round(px, 1),
                         "qty": qty, "invest": round(invest, 0),
                         "weight_pct": round(weight * 100, 1),
                         "stop": round(stop, 1), "risk_rupees": round(risk, 0),
                         "win_case_rupees": round(invest * aw / 100, 0),
                         "loss_case_rupees": round(invest * al / 100, 0),
                         "momentum_pct": round(E._get(e, date, "mom_raw") or 0, 0)})

    return {
        "date": str(date.date()),
        "risk_on": risk_on,
        "nifty": round(nifty, 0), "nifty_ma": round(nifty_ma, 0), "ma": ma,
        "headline": ("RISK-ON — the market is above its long-term trend, so the "
                     "strategy deploys into momentum leaders."
                     if risk_on else
                     "RISK-OFF — the Nifty is BELOW its 200-day trend. The strategy "
                     "stays in cash and opens no new positions. Hold existing "
                     "winners only while they keep trending."),
        "avg_win_pct": aw, "avg_loss_pct": al,
        "holdings_actions": actions,
        "buys": buys,
        "defensive_basket": defensive_rows,
        "target_equity_pct": round(eq_weight * 100),
        "target_defensive": {a.replace(".NS", ""): round(w * 100, 1)
                             for a, w in asset_weights.items() if w > 0.001},
        "cash": round(st["cash"], 0), "sleeve_equity": round(eq, 0),
    }
