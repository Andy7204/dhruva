"""Simulation engine — one decision step, reused by backtest and live run.

Design: a single `step_day` advances the portfolio by one trading day using only
information available up to that day (no lookahead). `run_backtest` loops it over
history; the live orchestrator calls it once on the latest bar. This guarantees
the paper book behaves exactly like the backtest that validated it.

Long-only. Fills at the day's close (config fill_mode) with slippage; stops and
targets are checked intrabar against the day's high/low. All transaction costs go
through the Groww model in costs.py.
"""
from __future__ import annotations

import math

from pathlib import Path

import numpy as np
import pandas as pd

from qlab import indicators as I
from qlab import strategies as S
from qlab import costs as C

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ------------------------------- panel build -------------------------------

def build_panel(market_raw: dict[str, pd.DataFrame], cfg: dict | None = None) -> dict[str, pd.DataFrame]:
    """Enrich each symbol and precompute signal/score/momentum columns.

    If cfg is given, the swing/short signal computation (slow Python state
    machines) is skipped for any sleeve with zero allocation — a big speedup on
    large universes when only momentum is active.
    """
    sleeves = (cfg or {}).get("sleeves", {})
    do_sw = sleeves.get("swing", {}).get("alloc", 1.0) > 0 if cfg else True
    do_st = sleeves.get("short_term", {}).get("alloc", 1.0) > 0 if cfg else True
    panel = {}
    for sym, df in market_raw.items():
        if df is None or len(df) < 210:
            continue
        e = I.enrich(df)
        sc_sw = S.sleeve_score("swing", e) if do_sw else None
        sc_st = S.sleeve_score("short_term", e) if do_st else None
        e["score_swing"] = sc_sw["score"] if do_sw else 0.0
        e["score_short"] = sc_st["score"] if do_st else 0.0
        e["desired_swing"] = (sc_sw["score"] >= S.THRESHOLD["swing"]).astype(float) if do_sw else 0.0
        e["desired_short"] = (sc_st["score"] >= S.THRESHOLD["short_term"]).astype(float) if do_st else 0.0
        e["trend_long"] = S.trend_filter(e)
        # Multi-factor momentum: classic 12-1 (12-month return skipping the last
        # month, to avoid short-term reversal) blended with 6-1, volatility-adjusted.
        # Only ranks names in an uptrend (above 200-DMA) with positive momentum.
        vol = e["vol20"].replace(0, np.nan)
        px = e["adjclose"]
        mom_12_1 = (px.shift(21) / px.shift(252) - 1.0) * 100
        mom_6_1 = (px.shift(21) / px.shift(126) - 1.0) * 100
        raw = 0.7 * mom_12_1 + 0.3 * mom_6_1
        e["mom_raw"] = raw
        e["mom_score"] = (raw / vol).where((px > e["sma200"]) & (raw > 0))
        # trailing daily turnover (INR) — liquidity screen + point-in-time size proxy
        e["turnover"] = (px * e["volume"]).rolling(60, min_periods=30).median()
        # how far above the 200-day line (for the anti-froth / extension filter)
        e["ext200"] = px / e["sma200"] - 1.0
        # store per-strategy fired columns for attribution/journaling
        if do_sw:
            for col in sc_sw.columns:
                if col != "score":
                    e[f"fire_{col}"] = sc_sw[col]
        if do_st:
            for col in sc_st.columns:
                if col != "score":
                    e[f"fire_{col}"] = sc_st[col]
        panel[sym] = e
    return panel


def trading_calendar(panel: dict[str, pd.DataFrame]) -> list[pd.Timestamp]:
    dates: set = set()
    for e in panel.values():
        dates.update(e.index.tolist())
    return sorted(dates)


# ------------------------------- portfolio ---------------------------------

def new_portfolio(cfg: dict) -> dict:
    cap = float(cfg["starting_capital"])
    sleeves = {}
    for name, s in cfg["sleeves"].items():
        c = round(cap * s["alloc"], 2)
        sleeves[name] = {"cash": c, "start_cash": c, "positions": {}}
    return {
        "as_of": None, "starting_capital": cap, "sleeves": sleeves,
        "realized_pnl": 0.0, "closed_trades": [], "equity_history": [],
        "run_count": 0, "rerank_counter": 0, "long_target_set": [],
        "charges_total": 0.0,  # ALL charges incl. basket rebalancing (closed_trades omit basket)
    }


def _get(e: pd.DataFrame, date, col):
    try:
        v = e.at[date, col]
        return None if pd.isna(v) else float(v)
    except (KeyError, TypeError, ValueError):  # ValueError guards a duplicated index
        return None


def _prices_at(panel, date) -> dict[str, float]:
    out = {}
    for sym, e in panel.items():
        p = _get(e, date, "adjclose")
        if p is not None:
            out[sym] = p
    return out


def sleeve_equity(sleeve_state: dict, prices: dict) -> float:
    mv = sum(pos["qty"] * prices.get(sym, pos["avg_price"])
             for sym, pos in sleeve_state["positions"].items())
    return sleeve_state["cash"] + mv


def total_equity(portfolio: dict, prices: dict) -> float:
    return sum(sleeve_equity(s, prices) for s in portfolio["sleeves"].values())


# ------------------------------ one step -----------------------------------

def _fired_names(e, date, sleeve) -> list[str]:
    prefix = "fire_"
    names = []
    for strat in S.STACKS[sleeve]:
        col = f"{prefix}{strat[0].__name__}"
        if col in e.columns and _get(e, date, col) == 1.0:
            names.append(strat[0].__name__)
    return names


import json as _json

_SECTORS: dict | None = None


def _sectors() -> dict:
    global _SECTORS
    if _SECTORS is None:
        p = PROJECT_ROOT / "data" / "nifty500_industry.json"
        try:
            _SECTORS = _json.loads(p.read_text())
        except Exception:
            _SECTORS = {}
    return _SECTORS


def _momentum_top_set(panel, date, k, cfg=None) -> list[str]:
    """Top-k by momentum, after a liquidity + anti-froth screen and a sector cap."""
    sel = (cfg or {}).get("selection", {})
    min_turn = sel.get("min_turnover", 0)
    max_ext = sel.get("max_extension", 0)  # 0 = off
    cap = sel.get("max_per_sector", 999)
    defensive = set((cfg or {}).get("defensive_basket", {}).keys()) | set((cfg or {}).get('excluded_momentum_assets', []))
    if (cfg or {}).get("defensive_asset"):
        defensive.add((cfg or {})["defensive_asset"])
    sectors = _sectors()

    ranked = []
    for sym, e in panel.items():
        if sym in defensive:
            continue  # diversifier basket (gold/silver/InvIT/cash), not a momentum pick
        m = _get(e, date, "mom_score")
        if m is None:
            continue
        if min_turn and (_get(e, date, "turnover") or 0) < min_turn:
            continue  # too illiquid to trade realistically (also a point-in-time size screen)
        if max_ext and (_get(e, date, "ext200") or 0) > max_ext:
            continue  # too far above trend — avoid buying parabolic froth
        ranked.append((m, sym))
    ranked.sort(reverse=True)

    chosen, sec_count = [], {}
    for _, sym in ranked:
        sec = sectors.get(sym) or sym  # unknown sector → its own bucket (don't lump all unknowns)
        if sec_count.get(sec, 0) >= cap:
            continue  # sector already full — force diversification
        chosen.append(sym)
        sec_count[sec] = sec_count.get(sec, 0) + 1
        if len(chosen) >= k:
            break
    return chosen


def _allocation(cfg: dict, panel: dict, date, regime_factor: float):
    """Return (equity_weight, {asset: target_weight}) for the long_term sleeve.

    'fixed' → the configured basket weights. 'adaptive' → tilt equity vs defensive
    by regime strength, and (if gated) drop any diversifier not trending up to cash.
    """
    basket = cfg.get("defensive_basket", {})
    alloc = cfg.get("allocation", {})
    if alloc.get("mode") != "adaptive":
        return 1.0 - sum(basket.values()), dict(basket)
    ew = alloc["equity_min"] + (alloc["equity_max"] - alloc["equity_min"]) * regime_factor
    dtot = max(0.0, 1.0 - ew)
    wsum = sum(basket.values()) or 1.0
    cash_asset = alloc.get("cash_asset")
    weights = {}
    for a, w in basket.items():
        share = dtot * (w / wsum)
        if (alloc.get("gate_diversifiers") and a != cash_asset
                and a in panel and date in panel[a].index):
            px = _get(panel[a], date, "adjclose"); s200 = _get(panel[a], date, "sma200")
            if px is not None and s200 is not None and px <= s200:
                share = 0.0  # diversifier not trending up → step aside to cash
        weights[a] = share
    return ew, weights


def step_day(portfolio: dict, panel: dict, date: pd.Timestamp, cfg: dict,
             weights: dict | None = None, regime_ok: bool = True,
             regime_factor: float = 1.0) -> list[dict]:
    """Advance the portfolio one day. Returns a list of decision events.

    regime_ok=False blocks all new entries (bear market) but still manages exits.
    regime_factor in (0,1] scales per-trade risk down in weaker regimes.
    """
    events: list[dict] = []
    slip = cfg.get("slippage_bps", 5) / 10000.0
    costs_cfg = cfg["costs"]
    prices = _prices_at(panel, date)
    dstr = pd.Timestamp(date).strftime("%Y-%m-%d")
    # regime_factor is used for allocation always; for position sizing only if size_scaling on
    size_factor = regime_factor if cfg.get("regime", {}).get("size_scaling") else 1.0

    # refresh long-term target set on the rerank cadence
    portfolio["rerank_counter"] += 1
    rr = cfg["rebalance"]["long_term_rerank_days"]
    if portfolio["rerank_counter"] % rr == 1 or not portfolio["long_target_set"]:
        k = cfg["sleeves"]["long_term"]["max_positions"]
        portfolio["long_target_set"] = _momentum_top_set(panel, date, k, cfg)
    long_set = set(portfolio["long_target_set"])

    for sleeve, sp in cfg["sleeves"].items():
        st = portfolio["sleeves"][sleeve]
        eq = sleeve_equity(st, prices)
        if sleeve == "long_term":
            eq_weight, asset_weights = _allocation(cfg, panel, date, regime_factor)
        else:
            eq_weight, asset_weights = 1.0, {}

        # ---- 1. manage / exit open positions ----
        for sym in list(st["positions"].keys()):
            pos = st["positions"][sym]
            if pos.get("strategy") in ("gold", "defensive"):
                continue  # diversifier basket is rebalanced separately, never stop/trend-exited
            e = panel.get(sym)
            if e is None or date not in e.index:
                continue
            high = _get(e, date, "adj_high") or _get(e, date, "adjclose")
            low = _get(e, date, "adj_low") or _get(e, date, "adjclose")
            close = _get(e, date, "adjclose")
            avg = pos["avg_price"]
            atr_now = _get(e, date, "atr14")
            pos["bars_held"] += 1
            pos["high_since"] = max(pos["high_since"], high)
            pos["low_since"] = min(pos["low_since"], low)
            pos["mfe"] = round(max(pos["mfe"], (high - avg) * pos["qty"]), 2)
            pos["mae"] = round(min(pos["mae"], (low - avg) * pos["qty"]), 2)

            trail = cfg.get("exits", {}).get("trail_atr_mult", {}).get(sleeve, 0.0)
            min_hold = cfg.get("entry_filters", {}).get("min_hold_days", {}).get(sleeve, 0)
            exit_price, reason = None, None
            if pos["stop"] and low <= pos["stop"]:
                exit_price, reason = pos["stop"], "stop"
            elif pos["target"] and pos["target"] > 0 and high >= pos["target"]:
                exit_price, reason = pos["target"], "target"
            elif pos["bars_held"] >= pos["max_hold_days"]:
                exit_price, reason = close, "time"
            elif pos["bars_held"] >= min_hold:  # signal/rank exit only after min-hold
                if sleeve == "long_term":
                    hold_ok = (_get(e, date, "trend_long") == 1.0) and (sym in long_set)
                else:
                    scol = "score_swing" if sleeve == "swing" else "score_short"
                    hold_ok = (_get(e, date, scol) or 0.0) >= 0.34
                if not hold_ok:
                    exit_price, reason = close, ("rebalance" if sleeve == "long_term" else "signal")

            if exit_price is not None:
                fill = exit_price * (1 - slip)
                gross = fill * pos["qty"]
                sell_ch = C.order_cost(gross, "sell", sym, sp["product"], costs_cfg)
                proceeds = gross - sell_ch
                cost_basis = pos["entry_value"] + pos["buy_charges"]
                net = proceeds - cost_basis
                st["cash"] = round(st["cash"] + proceeds, 2)
                portfolio["realized_pnl"] = round(portfolio["realized_pnl"] + net, 2)
                portfolio["charges_total"] = round(portfolio["charges_total"] + sell_ch, 2)
                trade = {
                    "symbol": sym, "sleeve": sleeve, "strategy": pos["strategy"],
                    "entry_date": pos["entry_date"], "exit_date": dstr,
                    "qty": pos["qty"], "entry_price": round(avg, 2),
                    "exit_price": round(fill, 2), "hold_days": pos["bars_held"],
                    "gross_pnl": round(gross - pos["entry_value"], 2),
                    "charges": round(pos["buy_charges"] + sell_ch, 2),
                    "net_pnl": round(net, 2),
                    "net_pnl_pct": round(net / cost_basis * 100, 2) if cost_basis else 0.0,
                    "exit_reason": reason, "mfe": pos["mfe"], "mae": pos["mae"],
                    "entry_signals": pos.get("entry_signals", []),
                }
                portfolio["closed_trades"].append(trade)
                events.append({"date": dstr, "action": "SELL", "sleeve": sleeve,
                               "symbol": sym, "qty": pos["qty"], "price": round(fill, 2),
                               "reason": reason, "net_pnl": round(net, 2),
                               "hold_days": pos["bars_held"]})
                del st["positions"][sym]
            elif trail and atr_now:  # not exited — ratchet the trailing stop for the NEXT bar
                chand = pos["high_since"] - trail * atr_now
                if chand > pos["stop"]:
                    pos["stop"] = round(chand, 2)

        # ---- 1b. diversifier basket: keep each asset at its (possibly adaptive) target weight ----
        basket = asset_weights if sleeve == "long_term" else {}
        want = [a for a, w in basket.items() if w > 0]  # positive-weight targets
        if basket and (portfolio["rerank_counter"] % rr == 1
                       or any(a not in st["positions"] for a in want)):
            eqn = sleeve_equity(st, prices)
            for asset, w in basket.items():
                if asset not in panel or date not in panel[asset].index:
                    continue
                aprice = _get(panel[asset], date, "adjclose")
                if not aprice:
                    continue
                apos = st["positions"].get(asset)
                cur = (apos["qty"] * aprice) if apos else 0.0
                diff = w * eqn - cur
                if w > 0 and diff > 0.05 * max(w * eqn, 1):  # buy toward target
                    qty = int(min(diff, st["cash"] * 0.98) // (aprice * (1 + slip)))
                    if qty >= 1:
                        fill = aprice * (1 + slip); grossv = fill * qty
                        ch = C.order_cost(grossv, "buy", asset, sp["product"], costs_cfg)
                        if st["cash"] >= grossv + ch:
                            st["cash"] = round(st["cash"] - grossv - ch, 2)
                            portfolio["charges_total"] = round(portfolio["charges_total"] + ch, 2)
                            if apos:
                                apos["qty"] += qty
                                apos["entry_value"] = round(apos["entry_value"] + grossv, 2)
                                apos["avg_price"] = round(apos["entry_value"] / apos["qty"], 2)
                                apos["buy_charges"] = round(apos["buy_charges"] + ch, 2)
                            else:
                                st["positions"][asset] = {
                                    "symbol": asset, "sleeve": sleeve, "qty": qty,
                                    "avg_price": round(fill, 2), "entry_date": dstr,
                                    "entry_value": round(grossv, 2), "buy_charges": round(ch, 2),
                                    "stop": 0.0, "target": 0.0, "max_hold_days": 10 ** 9,
                                    "strategy": "defensive", "bars_held": 0, "high_since": aprice,
                                    "low_since": aprice, "mfe": 0.0, "mae": 0.0,
                                    "entry_signals": ["defensive"], "thesis": f"diversifier {asset}"}
                            events.append({"date": dstr, "action": "BUY", "sleeve": sleeve,
                                           "symbol": asset, "qty": qty, "price": round(fill, 2),
                                           "reason": "diversifier"})
                # sell toward target — including a gated asset (w=0 → target 0 → sell it ALL)
                elif -diff > 0.05 * max(cur, 1) and apos:
                    qty = min(apos["qty"], max(1, int((-diff) // (aprice * (1 - slip)))))
                    fill = aprice * (1 - slip); grossv = fill * qty
                    ch = C.order_cost(grossv, "sell", asset, sp["product"], costs_cfg)
                    st["cash"] = round(st["cash"] + grossv - ch, 2)
                    portfolio["charges_total"] = round(portfolio["charges_total"] + ch, 2)
                    portfolio["realized_pnl"] = round(
                        portfolio["realized_pnl"] + grossv - ch - apos["avg_price"] * qty, 2)
                    orig = apos["qty"]
                    apos["qty"] -= qty
                    apos["buy_charges"] = round(apos["buy_charges"] * apos["qty"] / orig, 2) if orig else 0.0
                    apos["entry_value"] = round(apos["avg_price"] * apos["qty"], 2)
                    if apos["qty"] <= 0:
                        del st["positions"][asset]
                    events.append({"date": dstr, "action": "SELL", "sleeve": sleeve,
                                   "symbol": asset, "qty": qty, "price": round(fill, 2),
                                   "reason": "diversifier-rebalance"})

        # ---- 2. entries ----
        if not regime_ok:
            continue  # bear regime: manage exits only, open nothing new
        eq = sleeve_equity(st, prices)
        eq_names = eq * eq_weight  # equity portion (rest is the diversifier basket / cash)
        n_equity = sum(1 for p in st["positions"].values()
                       if p.get("strategy") not in ("gold", "defensive"))
        slots = sp["max_positions"] - n_equity
        if slots <= 0:
            continue
        held = set(st["positions"].keys())

        if sleeve == "long_term":
            cands = [(_get(panel[s], date, "mom_score"), s) for s in long_set
                     if s in panel and s not in held and date in panel[s].index
                     and _get(panel[s], date, "mom_score") is not None]
            cands.sort(reverse=True)
            candidates = [s for _, s in cands]
        else:
            scol = "score_swing" if sleeve == "swing" else "score_short"
            score_min = cfg.get("entry_filters", {}).get("score_min", {}).get(sleeve, 0.5)
            rank = []
            for s, e in panel.items():
                if s in held or date not in e.index:
                    continue
                sc = _get(e, date, scol) or 0.0
                if sc < score_min:  # conviction gate — fewer, higher-quality entries
                    continue
                sortkey = sc
                if sleeve == "short_term":
                    sortkey = (sortkey, -(_get(e, date, "rsi2") or 50))
                else:
                    sortkey = (sortkey, _get(e, date, "adx14") or 0)
                rank.append((sortkey, s))
            rank.sort(reverse=True)
            candidates = [s for _, s in rank]

        for sym in candidates:
            if slots <= 0:
                break
            e = panel[sym]
            price = _get(e, date, "adjclose")
            atr = _get(e, date, "atr14")
            if not price or not atr or atr <= 0:
                continue
            stop_dist = sp["atr_stop_mult"] * atr
            mode = sp.get("sizing")
            if mode == "equal_weight":
                qty_target = (eq_names / sp["max_positions"]) / price  # stay invested, low churn
            elif mode == "inverse_vol":
                v = _get(e, date, "vol20") or 0.30
                ref = cfg.get("sizing_ref_vol", 0.30)
                tilt = min(1.8, max(0.4, ref / v)) if v > 0 else 1.0  # smaller in riskier names
                qty_target = (eq_names / sp["max_positions"]) * size_factor * tilt / price
            else:
                risk_amt = eq_names * sp["risk_per_trade"] * size_factor  # risk-based sizing
                qty_target = risk_amt / stop_dist if stop_dist > 0 else 0
            qty_cap = (sp["max_pos_weight"] * eq) / price
            qty_cash = (st["cash"] * 0.98) / (price * (1 + slip))
            qty = int(math.floor(min(qty_target, qty_cap, qty_cash)))
            if qty < 1:
                continue
            fill = price * (1 + slip)
            gross = fill * qty
            buy_ch = C.order_cost(gross, "buy", sym, sp["product"], costs_cfg)
            if st["cash"] < gross + buy_ch:
                continue
            # cost-edge gate: expected move must clear the round-trip Groww cost by a margin
            sell_ch_est = C.order_cost(gross, "sell", sym, sp["product"], costs_cfg)
            cost_pct = (buy_ch + sell_ch_est) / gross * 100 if gross else 99
            exp_move_pct = ((sp["atr_target_mult"] if sp["atr_target_mult"] > 0
                             else sp["atr_stop_mult"]) * atr / price) * 100
            min_edge = cfg.get("entry_filters", {}).get("min_edge_to_cost", 0)
            if min_edge and exp_move_pct < min_edge * cost_pct:
                continue
            st["cash"] = round(st["cash"] - gross - buy_ch, 2)
            portfolio["charges_total"] = round(portfolio["charges_total"] + buy_ch, 2)
            fired = (["momentum"] if sleeve == "long_term" else _fired_names(e, date, sleeve))
            target = fill + sp["atr_target_mult"] * atr if sp["atr_target_mult"] > 0 else 0.0
            st["positions"][sym] = {
                "symbol": sym, "sleeve": sleeve, "qty": qty, "avg_price": round(fill, 2),
                "entry_date": dstr, "entry_value": round(gross, 2), "buy_charges": round(buy_ch, 2),
                "stop": round(fill - stop_dist, 2), "target": round(target, 2),
                "max_hold_days": sp["max_hold_days"], "strategy": "+".join(fired) or sleeve,
                "bars_held": 0, "high_since": price, "low_since": price,
                "mfe": 0.0, "mae": 0.0, "entry_signals": fired,
                "thesis": f"{sleeve}: {', '.join(fired)}; entry {price:.2f}, "
                          f"stop {fill - stop_dist:.2f} ({sp['atr_stop_mult']}xATR)",
            }
            events.append({"date": dstr, "action": "BUY", "sleeve": sleeve, "symbol": sym,
                           "qty": qty, "price": round(fill, 2),
                           "stop": round(fill - stop_dist, 2),
                           "reason": "+".join(fired) or sleeve,
                           "score": round(_get(e, date, "score_swing" if sleeve == "swing"
                                             else "score_short" if sleeve == "short_term"
                                             else "mom_score") or 0, 3)})
            slots -= 1

    portfolio["as_of"] = dstr
    portfolio["run_count"] += 1
    eq_total = total_equity(portfolio, prices)
    portfolio["equity_history"].append([dstr, round(eq_total, 2)])
    return events


# ------------------------------ backtest -----------------------------------

def regime_series(cfg: dict, benchmark_e: pd.DataFrame | None) -> pd.Series | None:
    if not cfg.get("regime", {}).get("enabled") or benchmark_e is None:
        return None
    ma = cfg["regime"]["ma"]
    return (benchmark_e["adjclose"] > I.sma(benchmark_e["adjclose"], ma))


def regime_factor_series(cfg: dict, benchmark_e: pd.DataFrame | None) -> pd.Series | None:
    """Regime strength in [floor,1]: 3-vote score (close>50DMA, close>200DMA, 50>200).

    Computed whenever the regime block is enabled (used for adaptive allocation and,
    if size_scaling is on, for position sizing).
    """
    r = cfg.get("regime", {})
    if not r.get("enabled") or benchmark_e is None:
        return None
    px = benchmark_e["adjclose"]
    s50, s200 = I.sma(px, 50), I.sma(px, 200)
    votes = (px > s50).astype(float) + (px > s200).astype(float) + (s50 > s200).astype(float)
    floor = r.get("factor_floor", 0.4)
    return (floor + (1 - floor) * votes / 3.0)


def run_backtest(cfg: dict, panel: dict, weights: dict | None = None,
                 warmup: int = 260, start=None, end=None,
                 benchmark_e: pd.DataFrame | None = None) -> dict:
    cal = trading_calendar(panel)
    if start:
        cal = [d for d in cal if d >= pd.Timestamp(start)]
    else:
        cal = cal[warmup:]
    if end:
        cal = [d for d in cal if d <= pd.Timestamp(end)]
    regime = regime_series(cfg, benchmark_e)
    rfactor = regime_factor_series(cfg, benchmark_e)
    pf = new_portfolio(cfg)
    all_events = []
    for date in cal:
        rok = True if regime is None else bool(regime.get(date, True))
        rf = 1.0 if rfactor is None else float(rfactor.get(date, 1.0))
        all_events.extend(step_day(pf, panel, date, cfg, weights, regime_ok=rok, regime_factor=rf))
    eq = pd.Series({pd.Timestamp(d): v for d, v in pf["equity_history"]})
    return {"portfolio": pf, "equity": eq, "events": all_events,
            "closed_trades": pf["closed_trades"]}


if __name__ == "__main__":
    from qlab import data as D
    from qlab import metrics as M
    cfg = D.load_config()
    print("Loading data ...")
    raw = D.get_universe(cfg["universe"], rng=cfg["data"]["backtest_range"])
    bench = I.enrich(D.get_history(cfg["regime"]["benchmark"], rng=cfg["data"]["backtest_range"]))
    panel = build_panel(raw)
    print(f"Panel: {len(panel)} symbols. Running backtests ...")

    cfg_off = dict(cfg); cfg_off["regime"] = dict(cfg["regime"]); cfg_off["regime"]["enabled"] = False
    res_off = run_backtest(cfg_off, panel)
    res = run_backtest(cfg, panel, benchmark_e=bench)
    m_off = M.compute_metrics(res_off["equity"], res_off["closed_trades"])
    m = M.compute_metrics(res["equity"], res["closed_trades"])

    # Nifty buy & hold over the same window
    eq = res["equity"]
    bslice = bench["adjclose"].reindex(eq.index).dropna()
    bh_ret = (bslice.iloc[-1] / bslice.iloc[0] - 1) * 100 if len(bslice) > 2 else 0.0

    print("\n=== SYSTEM BACKTEST — regime filter OFF vs ON ===")
    keys = ["final_equity", "total_return_pct", "cagr_pct", "sharpe", "sortino",
            "max_drawdown_pct", "num_trades", "win_rate_pct", "profit_factor",
            "expectancy", "total_charges"]
    print(f"  {'metric':20s} {'OFF':>14s} {'ON':>14s}")
    for k in keys:
        print(f"  {k:20s} {str(m_off[k]):>14s} {str(m[k]):>14s}")
    print(f"\n  Nifty buy&hold over same window: {bh_ret:.1f}%")
    print("\n=== per-sleeve expectancy ===")
    from collections import defaultdict
    agg = defaultdict(list)
    for t in res["closed_trades"]:
        agg[t["sleeve"]].append(t["net_pnl"])
    for sl, pnls in agg.items():
        arr = np.array(pnls)
        print(f"  {sl:11s} trades={len(arr):3d} win%={ (arr>0).mean()*100:4.1f} "
              f"expectancy=Rs{arr.mean():7.1f} total=Rs{arr.sum():9.1f}")
