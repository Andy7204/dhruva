"""Consolidated validation — trust the algo or don't.

Runs on the improved momentum algo (liquidity + sector-cap + conservative costs):
  1. Full-window and walk-forward (out-of-sample) vs Nifty on the 500 universe.
  2. Survivorship-robust cross-check on the Nifty-100 (large caps rarely delist,
     so this list has far less survivorship bias than the 500).
  3. Beats-basic-strategies check: vs Nifty buy&hold and vs owning all stocks
     equally (equal-weight buy&hold).
  4. Year-by-year returns vs Nifty (is the edge consistent or one lucky year?).
Saves a compact summary to runs/validation.json for the dashboard.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qlab import data as D, indicators as I, engine as E, metrics as M, optimize as O  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def nifty_ret(bench_close, eq):
    bb = bench_close.reindex(eq.index).ffill().dropna()
    return round((bb.iloc[-1] / bb.iloc[0] - 1) * 100, 1) if len(bb) > 2 else 0.0


def equal_weight_bh(panel, dates):
    """Own every stock equally, buy & hold — a 'dumb' baseline."""
    norm = []
    for e in panel.values():
        s = e["adjclose"].reindex(dates).ffill()
        if s.notna().sum() > len(dates) * 0.8:
            norm.append(s / s.dropna().iloc[0])
    if not norm:
        return 0.0
    idx = pd.concat(norm, axis=1).mean(axis=1).dropna()
    return round((idx.iloc[-1] / idx.iloc[0] - 1) * 100, 1)


def main():
    cfg = D.load_config()
    print("Loading data + building panel (fast, momentum-only)...")
    raw = D.get_universe(cfg["universe"], rng=cfg["data"]["backtest_range"])
    bench = I.enrich(D.get_history(cfg["regime"]["benchmark"], rng=cfg["data"]["backtest_range"]))
    panel = E.build_panel(raw, cfg)
    b = bench["adjclose"]
    print(f"Panel: {len(panel)} symbols\n")

    out = {}

    # 1. full-window + walk-forward on 500
    r = E.run_backtest(cfg, panel, benchmark_e=bench, warmup=260)
    eq = r["equity"]; m = M.compute_metrics(eq, r["closed_trades"])
    out["full_500"] = {"ret": m["total_return_pct"], "nifty": nifty_ret(b, eq),
                       "sharpe": m["sharpe"], "dd": m["max_drawdown_pct"],
                       "trades": m["num_trades"], "fees": m["total_charges"]}
    print(f"[500 full] trader {m['total_return_pct']:+.1f}% vs Nifty {out['full_500']['nifty']:+.1f}%  "
          f"Sharpe {m['sharpe']} DD {m['max_drawdown_pct']}%")

    wf = O.walk_forward(cfg, panel, bench, O.DEFAULT_GRID, n_folds=4, warmup=260, verbose=False)
    oos = wf["combined_oos_equity"]; cm = wf["combined_oos_metrics"]
    out["wf_500"] = {"ret": cm["total_return_pct"], "nifty": nifty_ret(b, oos),
                     "sharpe": cm["sharpe"], "dd": cm["max_drawdown_pct"],
                     "folds": [{"test": f["test"], "oos": f["OOS_return"]} for f in wf["folds"]]}
    print(f"[500 walk-fwd OOS] trader {cm['total_return_pct']:+.1f}% vs Nifty {out['wf_500']['nifty']:+.1f}%  "
          f"Sharpe {cm['sharpe']} DD {cm['max_drawdown_pct']}%")

    # 2. survivorship-robust: Nifty-100 subset
    n100 = set((ROOT / "data" / "nifty100.txt").read_text().split())
    panel100 = {s: e for s, e in panel.items() if s in n100}
    r100 = E.run_backtest(cfg, panel100, benchmark_e=bench, warmup=260)
    m100 = M.compute_metrics(r100["equity"], r100["closed_trades"])
    wf100 = O.walk_forward(cfg, panel100, bench, O.DEFAULT_GRID, n_folds=4, warmup=260, verbose=False)
    cm100 = wf100["combined_oos_metrics"]
    out["n100"] = {"n": len(panel100),
                   "full_ret": m100["total_return_pct"], "full_nifty": nifty_ret(b, r100["equity"]),
                   "wf_ret": cm100["total_return_pct"], "wf_nifty": nifty_ret(b, wf100["combined_oos_equity"]),
                   "wf_sharpe": cm100["sharpe"], "wf_dd": cm100["max_drawdown_pct"]}
    print(f"[Nifty100 survivorship-robust] full {m100['total_return_pct']:+.1f}% | "
          f"walk-fwd OOS {cm100['total_return_pct']:+.1f}% vs Nifty {out['n100']['wf_nifty']:+.1f}%  "
          f"Sharpe {cm100['sharpe']}")

    # 3. basic-strategy baselines over the full window
    ewbh = equal_weight_bh(panel, eq.index)
    out["baselines"] = {"nifty_bh": out["full_500"]["nifty"], "equal_weight_bh": ewbh}
    print(f"[baselines] Nifty buy&hold {out['full_500']['nifty']:+.1f}% | own-all-equally {ewbh:+.1f}%")

    # 4. year-by-year (strategy vs Nifty)
    yb = {}
    for yr, grp in eq.groupby(eq.index.year):
        if len(grp) < 5:
            continue
        s_ret = (grp.iloc[-1] / grp.iloc[0] - 1) * 100
        byr = b.reindex(grp.index).ffill().dropna()
        n_ret = (byr.iloc[-1] / byr.iloc[0] - 1) * 100 if len(byr) > 2 else 0
        yb[str(yr)] = {"trader": round(s_ret, 1), "nifty": round(n_ret, 1),
                       "beat": bool(s_ret > n_ret)}
    out["year_by_year"] = yb
    print("\nYear-by-year (trader vs Nifty):")
    for yr, v in yb.items():
        print(f"  {yr}: trader {v['trader']:+6.1f}%  Nifty {v['nifty']:+6.1f}%  {'BEAT' if v['beat'] else 'lag'}")

    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / "validation.json").write_text(json.dumps(out, indent=2))
    print("\nSaved runs/validation.json")


if __name__ == "__main__":
    main()
