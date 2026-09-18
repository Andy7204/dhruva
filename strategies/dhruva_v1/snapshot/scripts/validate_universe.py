"""Validate the strategy on an arbitrary universe file (e.g. the full NSE list).

    python scripts/validate_universe.py data/nse_all.txt

Applies an 'ever-liquid' pre-filter (keeps names whose trailing turnover cleared a
floor at some point in history) purely for tractability — the engine's own
point-in-time turnover filter still governs which names are tradable on each date.
Reports full-window + walk-forward (OOS) + year-by-year vs Nifty.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qlab import data as D, indicators as I, engine as E, metrics as M, optimize as O  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ufile = sys.argv[1] if len(sys.argv) > 1 else "data/nse_all.txt"
    min_turn_ever = float(sys.argv[2]) if len(sys.argv) > 2 else 2e7  # ₹2cr ever
    cfg = D.load_config()
    syms = [s.strip() for s in (ROOT / ufile).read_text().splitlines() if s.strip()]
    # make sure the diversifier basket is present too
    for a in cfg.get("defensive_basket", {}):
        if a not in syms:
            syms.append(a)
    print(f"Loading {len(syms)} symbols from {ufile} ...")
    raw = D.get_universe(syms, rng=cfg["data"]["backtest_range"])
    bench = I.enrich(D.get_history(cfg["regime"]["benchmark"], rng=cfg["data"]["backtest_range"]))

    # 'ever-liquid' pre-filter for tractability (not a point-in-time decision)
    keep = {}
    for s, df in raw.items():
        if df is None or len(df) < 260:
            continue
        if s in cfg.get("defensive_basket", {}):
            keep[s] = df; continue
        turn = (df["adjclose"] * df["volume"]).rolling(60, min_periods=30).median()
        if turn.max() >= min_turn_ever:
            keep[s] = df
    print(f"After ever-liquid filter (>=₹{min_turn_ever/1e7:.0f}cr): {len(keep)} names. Building panel ...")
    panel = E.build_panel(keep, cfg)
    print(f"Panel: {len(panel)} symbols")
    b = bench["adjclose"]

    def nifty(eq):
        bb = b.reindex(eq.index).ffill().dropna()
        return (bb.iloc[-1] / bb.iloc[0] - 1) * 100 if len(bb) > 2 else 0.0

    r = E.run_backtest(cfg, panel, benchmark_e=bench, warmup=260)
    eq = r["equity"]; m = M.compute_metrics(eq, r["closed_trades"])
    print(f"\n[FULL] trader {m['total_return_pct']:+.1f}% vs Nifty {nifty(eq):+.1f}%  "
          f"Sharpe {m['sharpe']} DD {m['max_drawdown_pct']}% trades {m['num_trades']} fees {m['total_charges']:.0f}")
    print("Year-by-year:")
    for yr, g in eq.groupby(eq.index.year):
        if len(g) < 5:
            continue
        s = (g.iloc[-1] / g.iloc[0] - 1) * 100
        by = b.reindex(g.index).ffill().dropna(); n = (by.iloc[-1] / by.iloc[0] - 1) * 100
        print(f"  {yr}: trader {s:+6.1f}%  Nifty {n:+6.1f}%  {'BEAT' if s > n else 'lag'}")

    print("\nWalk-forward (out-of-sample) ...")
    wf = O.walk_forward(cfg, panel, bench, O.DEFAULT_GRID, n_folds=4, warmup=260, verbose=False)
    cm = wf["combined_oos_metrics"]
    print(f"[WALK-FWD OOS] trader {cm['total_return_pct']:+.1f}% vs Nifty {nifty(wf['combined_oos_equity']):+.1f}%  "
          f"Sharpe {cm['sharpe']} DD {cm['max_drawdown_pct']}%")


if __name__ == "__main__":
    main()
