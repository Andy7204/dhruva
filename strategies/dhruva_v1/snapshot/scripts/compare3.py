"""Head-to-head: Aggressive-smart vs Balanced vs Core-satellite 70/30, each at ₹1L.

Full-window backtest (fixed rules, no look-ahead) on the Nifty-500 universe.
Reports year-by-year vs Nifty (and how many years each beats it) plus the full
ratio set (CAGR, Sharpe, Sortino, Calmar, max drawdown).
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
    b = bench["adjclose"]

    AGG = {"defensive_basket": {}, "allocation.mode": "fixed", "regime.enabled": True}
    BAL = {"allocation.mode": "adaptive"}
    ra = E.run_backtest(_apply(cfg, AGG), panel, benchmark_e=bench)["equity"]
    rb = E.run_backtest(_apply(cfg, BAL), panel, benchmark_e=bench)["equity"]
    idx = ra.index.intersection(rb.index)
    ra, rb = ra.reindex(idx).ffill(), rb.reindex(idx).ffill()
    # core-satellite 70/30 = 70% balanced + 30% aggressive, daily-rebalanced returns
    cs = (1 + 0.7 * rb.pct_change().fillna(0) + 0.3 * ra.pct_change().fillna(0)).cumprod() * cfg["starting_capital"]
    curves = {"Aggressive-smart": ra, "Balanced": rb, "Core-satellite 70/30": cs}

    bb = b.reindex(idx).ffill()
    print(f"Window {idx[0].date()} → {idx[-1].date()} · ₹1,00,000 start · Nifty "
          f"{(bb.iloc[-1]/bb.iloc[0]-1)*100:+.0f}% over the whole period\n")

    # year-by-year
    years = sorted(set(idx.year))
    print(f"{'Year':6s}{'Nifty':>9s}" + "".join(f"{n[:16]:>18s}" for n in curves))
    beats = {n: 0 for n in curves}
    nyears = 0
    for yr in years:
        m = idx.year == yr
        if m.sum() < 5:
            continue
        nyears += 1
        ny = (bb[m].iloc[-1] / bb[m].iloc[0] - 1) * 100
        row = f"{yr:6d}{ny:>+8.1f}%"
        for n, c in curves.items():
            cr = (c[m].iloc[-1] / c[m].iloc[0] - 1) * 100
            if cr > ny:
                beats[n] += 1
            row += f"{cr:>+17.1f}%"
        print(row)

    print(f"\n{'':6s}{'':>9s}" + "".join(f"{'beats '+str(beats[n])+'/'+str(nyears):>18s}" for n in curves))

    print(f"\n{'Ratio':16s}" + "".join(f"{n[:16]:>18s}" for n in curves))
    metrics = {n: M.compute_metrics(c, []) for n, c in curves.items()}
    for key, lbl in [("total_return_pct", "Total return %"), ("cagr_pct", "CAGR %"),
                     ("sharpe", "Sharpe"), ("sortino", "Sortino"),
                     ("calmar", "Calmar"), ("max_drawdown_pct", "Max drawdown %")]:
        print(f"{lbl:16s}" + "".join(f"{metrics[n][key]:>18}" for n in curves))

    # save for the dashboard's "Backtested runs" section
    import json
    yby = {}
    for yr in years:
        m = idx.year == yr
        if m.sum() < 5:
            continue
        yby[str(yr)] = {"Nifty": round((bb[m].iloc[-1] / bb[m].iloc[0] - 1) * 100, 1),
                        **{n: round((c[m].iloc[-1] / c[m].iloc[0] - 1) * 100, 1) for n, c in curves.items()}}
    # weekly-sampled equity curves (normalised to ₹1L) to keep the file small
    def wk(s):
        w = s.resample("W").last().dropna()
        return [[str(i.date()), round(float(v), 0)] for i, v in w.items()]
    nb = bb / bb.iloc[0] * cfg["starting_capital"]
    out = {"window": [str(idx[0].date()), str(idx[-1].date())],
           "nifty_total": round((bb.iloc[-1] / bb.iloc[0] - 1) * 100, 1),
           "years": len(yby), "year_by_year": yby,
           "ratios": {n: {k: metrics[n][k] for k in
                          ["total_return_pct", "cagr_pct", "sharpe", "sortino", "calmar", "max_drawdown_pct"]}
                      for n in curves},
           "beats": beats,
           "curves": {**{n: wk(c) for n, c in curves.items()}, "Nifty": wk(nb)}}
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / "backtest_comparison.json").write_text(json.dumps(out))
    print("\nSaved runs/backtest_comparison.json")


if __name__ == "__main__":
    main()
