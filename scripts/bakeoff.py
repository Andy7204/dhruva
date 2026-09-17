"""Standardized bake-off: every approach on the SAME universe + window, fixed
rules (no parameter fitting to the test data → no look-ahead). Reports comparable
return / CAGR / Sharpe / Sortino / maxDD / Calmar so the approaches can be ranked
apples-to-apples. Also builds a core-satellite (70% safe + 30% aggressive) blend.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qlab import data as D, indicators as I, engine as E, metrics as M  # noqa: E402
from qlab.optimize import _apply  # noqa: E402


def main():
    cfg = D.load_config()
    raw = D.get_universe(cfg["universe"], rng=cfg["data"]["backtest_range"])
    bench = I.enrich(D.get_history("^NSEI", rng=cfg["data"]["backtest_range"]))
    panel = E.build_panel(raw, cfg)
    print(f"panel {len(panel)}")

    approaches = {
        "Pure momentum (100% eq, top15)":
            {"defensive_basket": {}, "allocation.mode": "fixed", "regime.enabled": False},
        "Momentum + crash filter":
            {"defensive_basket": {}, "allocation.mode": "fixed", "regime.enabled": True},
        "Momentum + 40% gold":
            {"defensive_basket": {"GOLDBEES.NS": 0.40}, "allocation.mode": "fixed", "regime.enabled": True},
        "Momentum + basket (fixed)":
            {"allocation.mode": "fixed"},
        "Momentum + basket + adaptive":
            {"allocation.mode": "adaptive"},
        "AGGRESSIVE (top10, 100% eq, no crash filter)":
            {"defensive_basket": {}, "allocation.mode": "fixed", "regime.enabled": False,
             "sleeves.long_term.max_positions": 10},
    }
    results = {}
    equities = {}
    for name, ov in approaches.items():
        c = _apply(cfg, ov)
        r = E.run_backtest(c, panel, benchmark_e=bench, warmup=260)
        eq = r["equity"]; equities[name] = eq
        results[name] = M.compute_metrics(eq, r["closed_trades"])
        print(f"  done: {name}")

    idx = list(equities.values())[0].index

    # baselines on the same window
    b = bench["adjclose"].reindex(idx).ffill().dropna()
    results["Nifty buy & hold"] = M.compute_metrics(b / b.iloc[0] * cfg["starting_capital"], [])
    equities["Nifty buy & hold"] = b / b.iloc[0] * cfg["starting_capital"]
    ew = []
    for e in panel.values():
        s = e["adjclose"].reindex(idx).ffill()
        if s.notna().sum() > len(idx) * 0.8:
            ew.append(s / s.dropna().iloc[0])
    ewc = pd.concat(ew, axis=1).mean(axis=1).dropna() * cfg["starting_capital"]
    results["Own all equally"] = M.compute_metrics(ewc, [])
    equities["Own all equally"] = ewc

    # core-satellite: 70% (basket+adaptive) + 30% aggressive, daily-rebalanced returns
    g = equities["Momentum + basket + adaptive"].pct_change().fillna(0)
    h = equities["AGGRESSIVE (top10, 100% eq, no crash filter)"].pct_change().fillna(0)
    cs = (1 + 0.7 * g + 0.3 * h).cumprod() * cfg["starting_capital"]
    results["Core-satellite 70/30"] = M.compute_metrics(cs, [])

    order = ["Nifty buy & hold", "Own all equally", "Pure momentum (100% eq, top15)",
             "Momentum + crash filter", "Momentum + 40% gold", "Momentum + basket (fixed)",
             "Momentum + basket + adaptive", "AGGRESSIVE (top10, 100% eq, no crash filter)",
             "Core-satellite 70/30"]
    print(f"\nSAME universe (Nifty-500) + window {idx[0].date()}→{idx[-1].date()}, fixed rules (no look-ahead)\n")
    print(f"{'approach':46s}{'ret%':>8s}{'CAGR%':>7s}{'Sharpe':>7s}{'Sortino':>8s}{'maxDD%':>8s}{'Calmar':>7s}")
    for name in order:
        m = results[name]
        print(f"{name:46s}{m['total_return_pct']:8.0f}{m['cagr_pct']:7.1f}{m['sharpe']:7.2f}"
              f"{m['sortino']:8.2f}{m['max_drawdown_pct']:8.0f}{m['calmar']:7.2f}")


if __name__ == "__main__":
    main()
