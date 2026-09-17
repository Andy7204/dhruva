"""Learning loop — post-mortem attribution + adaptive strategy weights.

The system reviews its own closed trades and:
  1. writes a per-trade post-mortem (why it worked / failed),
  2. attributes P&L to each base strategy that participated in the entry,
  3. proposes new strategy weights (down-weight persistent losers, keep winners),
  4. emits human-readable "learnings".

Weights are consumed by strategies.sleeve_score(), closing the feedback loop:
what loses money after costs gets a smaller vote next run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_PATH = PROJECT_ROOT / "runs" / "weights.json"

MIN_TRADES = 15          # need this many participations before we trust a strategy
EXPECTANCY_SCALE = 60.0  # INR; tanh scale for the weight multiplier
W_LO, W_HI = 0.25, 1.5


def post_mortem(trade: dict) -> dict:
    """Structured explanation + lesson tag for one closed trade."""
    net = trade["net_pnl"]
    reason = trade["exit_reason"]
    mfe, mae = trade.get("mfe", 0.0), trade.get("mae", 0.0)
    win = net > 0
    if reason == "target":
        lesson = "Target hit — thesis played out."
    elif reason == "stop":
        lesson = ("Stopped out. Entry ran straight into a loss; "
                  "trend/timing was wrong or stop too tight.")
    elif reason == "time":
        lesson = ("Time-exit. Signal decayed without resolving — "
                  "'dead money', consider a shorter max-hold." if not win
                  else "Time-exit in profit — trailing could have captured more.")
    elif reason in ("signal", "rebalance"):
        lesson = ("Signal/rank exit at a loss — the edge reversed."
                  if not win else "Signal/rank exit banking a gain.")
    else:
        lesson = "Closed."
    # give-back check: did we leave a lot of open profit on the table?
    giveback = ""
    if mfe > 0 and net < 0.5 * mfe:
        giveback = f" Left ~Rs{mfe - max(net,0):.0f} of peak profit on the table."
    return {
        "symbol": trade["symbol"], "sleeve": trade["sleeve"],
        "strategy": trade["strategy"], "net_pnl": net,
        "net_pnl_pct": trade.get("net_pnl_pct", 0.0),
        "hold_days": trade.get("hold_days", 0), "exit_reason": reason,
        "verdict": "WIN" if win else "LOSS",
        "lesson": lesson + giveback,
    }


def _weight_from_expectancy(expectancy: float, n: int) -> float:
    if n < MIN_TRADES:
        return 1.0
    mult = 1.0 + math.tanh(expectancy / EXPECTANCY_SCALE)
    return round(min(W_HI, max(W_LO, mult)), 3)


def review(closed_trades: list[dict]) -> dict:
    """Analyse all closed trades → weights + learnings. Returns a report dict."""
    # participation attribution: credit each trade to every base strategy fired
    by_strat: dict[str, list[float]] = {}
    by_sleeve: dict[str, list[float]] = {}
    by_reason: dict[str, list[float]] = {}
    for t in closed_trades:
        by_sleeve.setdefault(t["sleeve"], []).append(t["net_pnl"])
        by_reason.setdefault(t["exit_reason"], []).append(t["net_pnl"])
        for s in (t.get("entry_signals") or [t.get("strategy", "?")]):
            by_strat.setdefault(s, []).append(t["net_pnl"])

    weights, strat_stats = {}, {}
    for s, pnls in by_strat.items():
        arr = np.array(pnls, dtype=float)
        exp = float(arr.mean())
        w = _weight_from_expectancy(exp, len(arr))
        weights[s] = w
        strat_stats[s] = {"trades": len(arr), "expectancy": round(exp, 1),
                          "win_rate_pct": round((arr > 0).mean() * 100, 1),
                          "total_pnl": round(float(arr.sum()), 1), "weight": w}

    sleeve_stats = {sl: {"trades": len(p), "expectancy": round(float(np.mean(p)), 1),
                         "win_rate_pct": round((np.array(p) > 0).mean() * 100, 1),
                         "total_pnl": round(float(np.sum(p)), 1)}
                    for sl, p in by_sleeve.items()}
    reason_stats = {r: {"trades": len(p), "total_pnl": round(float(np.sum(p)), 1)}
                    for r, p in by_reason.items()}

    learnings = _narrate(strat_stats, sleeve_stats, reason_stats, closed_trades)
    return {"weights": weights, "strategy_stats": strat_stats,
            "sleeve_stats": sleeve_stats, "reason_stats": reason_stats,
            "learnings": learnings}


def _narrate(strat_stats, sleeve_stats, reason_stats, trades) -> list[str]:
    out = []
    for s, st in sorted(strat_stats.items(), key=lambda kv: kv[1]["expectancy"]):
        if st["trades"] < MIN_TRADES:
            continue
        verb = "down-weighted" if st["weight"] < 1 else ("boosted" if st["weight"] > 1 else "kept")
        out.append(f"{s}: {st['trades']} trades, {st['win_rate_pct']}% win, "
                   f"expectancy Rs{st['expectancy']} → {verb} to {st['weight']}")
    best = max(sleeve_stats.items(), key=lambda kv: kv[1]["total_pnl"], default=None)
    worst = min(sleeve_stats.items(), key=lambda kv: kv[1]["total_pnl"], default=None)
    if best:
        out.append(f"Best sleeve: {best[0]} (Rs{best[1]['total_pnl']}); "
                   f"worst: {worst[0]} (Rs{worst[1]['total_pnl']}).")
    if trades:
        charges = sum(t.get("charges", 0) for t in trades)
        gross = sum(t.get("gross_pnl", 0) for t in trades)
        out.append(f"Charges consumed Rs{charges:.0f} vs gross P&L Rs{gross:.0f} "
                   f"— costs are {abs(charges / gross) * 100:.0f}% of gross." if gross
                   else f"Charges Rs{charges:.0f} on zero gross P&L — over-trading.")
    stopped = reason_stats.get("stop", {}).get("trades", 0)
    timed = reason_stats.get("time", {}).get("trades", 0)
    if stopped + timed:
        out.append(f"Exit mix: {stopped} stop-outs, {timed} time-exits, "
                   f"{reason_stats.get('target', {}).get('trades', 0)} targets hit.")
    return out


def save_weights(weights: dict) -> None:
    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS_PATH.write_text(json.dumps(weights, indent=2))


def load_weights() -> dict:
    if WEIGHTS_PATH.exists():
        return json.loads(WEIGHTS_PATH.read_text())
    return {}
