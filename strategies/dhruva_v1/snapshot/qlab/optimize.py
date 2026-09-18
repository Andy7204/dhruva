"""Walk-forward optimization — the honest refinement engine.

Grid-search parameters on a TRAIN window, pick the best by an objective (Sharpe
by default), then measure on the immediately-following TEST window the params
never saw. Roll forward and stitch the out-of-sample (OOS) results together.

The gap between in-sample and OOS performance is the overfitting tax; we report
both so a good-looking in-sample number can't masquerade as an edge.

This is the disciplined stand-in for "backprop/optimization": parameter search
under strict out-of-sample validation, not curve-fitting the whole history.
"""
from __future__ import annotations

import copy
import itertools

import numpy as np
import pandas as pd

from qlab import engine as E
from qlab import metrics as M


def _apply(cfg: dict, overrides: dict) -> dict:
    """Apply dotted-path overrides to a deep copy of cfg. e.g. 'sleeves.swing.atr_stop_mult'."""
    c = copy.deepcopy(cfg)
    for path, val in overrides.items():
        node = c
        parts = path.split(".")
        for p in parts[:-1]:
            node = node[p]
        node[parts[-1]] = val
    return c


def run_grid_point(cfg: dict, panel: dict, bench_e, overrides: dict,
                   start, end) -> dict:
    c = _apply(cfg, overrides)
    res = E.run_backtest(c, panel, start=start, end=end, benchmark_e=bench_e)
    return M.compute_metrics(res["equity"], res["closed_trades"])


def expand_grid(grid: dict) -> list[dict]:
    keys = list(grid.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*[grid[k] for k in keys])]


def walk_forward(cfg: dict, panel: dict, bench_e, grid: dict,
                 n_folds: int = 4, objective: str = "sharpe",
                 warmup: int = 260, verbose: bool = True) -> dict:
    cal = E.trading_calendar(panel)[warmup:]
    fold_len = len(cal) // (n_folds + 1)  # first block is pure train
    combos = expand_grid(grid)
    if verbose:
        print(f"Walk-forward: {len(combos)} param sets x {n_folds} folds "
              f"({fold_len} days each). Objective: {objective}.")

    oos_equity_pieces, chosen = [], []
    for f in range(n_folds):
        tr_start = cal[0]
        tr_end = cal[(f + 1) * fold_len - 1]
        te_start = cal[(f + 1) * fold_len]
        te_end = cal[min((f + 2) * fold_len - 1, len(cal) - 1)]

        best, best_obj, best_is = None, -1e9, None
        for ov in combos:
            m = run_grid_point(cfg, panel, bench_e, ov, tr_start, tr_end)
            score = m.get(objective, -1e9)
            if score > best_obj:
                best_obj, best, best_is = score, ov, m
        # evaluate best params OOS
        c = _apply(cfg, best)
        res = E.run_backtest(c, panel, start=te_start, end=te_end, benchmark_e=bench_e)
        oos_m = M.compute_metrics(res["equity"], res["closed_trades"])
        chosen.append({"fold": f + 1, "train_end": str(tr_end.date()),
                       "test": f"{te_start.date()}→{te_end.date()}",
                       "params": best, "IS_sharpe": best_is["sharpe"],
                       "OOS_sharpe": oos_m["sharpe"], "OOS_return": oos_m["total_return_pct"]})
        oos_equity_pieces.append(res["equity"])
        if verbose:
            print(f"  fold {f+1}: best={best} IS_sharpe={best_is['sharpe']} "
                  f"→ OOS_sharpe={oos_m['sharpe']} OOS_ret={oos_m['total_return_pct']}%")

    # stitch OOS pieces (each starts fresh at 1L; chain returns for a combined curve)
    combined = _chain_equity(oos_equity_pieces)
    comb_m = M.compute_metrics(combined, [])
    return {"folds": chosen, "combined_oos_equity": combined,
            "combined_oos_metrics": comb_m}


def _chain_equity(pieces: list[pd.Series]) -> pd.Series:
    out, base = [], 1.0
    for p in pieces:
        if len(p) < 2:
            continue
        norm = p / p.iloc[0] * base
        out.append(norm)
        base = norm.iloc[-1]
    if not out:
        return pd.Series(dtype=float)
    return pd.concat(out)


# momentum grid: how many names to hold, and how often to rebalance.
# every extra combo costs a backtest, so keep it tiny.
DEFAULT_GRID = {
    "sleeves.long_term.max_positions": [15, 20],
    "rebalance.long_term_rerank_days": [42, 63],
}


if __name__ == "__main__":
    from qlab import data as D
    from qlab import indicators as I
    cfg = D.load_config()
    print("Loading data ...")
    raw = D.get_universe(cfg["universe"], rng=cfg["data"]["backtest_range"])
    bench = I.enrich(D.get_history(cfg["regime"]["benchmark"], rng=cfg["data"]["backtest_range"]))
    panel = E.build_panel(raw)
    res = walk_forward(cfg, panel, bench, DEFAULT_GRID, n_folds=3)
    print("\n=== Combined OUT-OF-SAMPLE metrics (chained folds) ===")
    for k in ["total_return_pct", "cagr_pct", "sharpe", "sortino", "max_drawdown_pct"]:
        print(f"  {k:20s} {res['combined_oos_metrics'][k]}")
    print("\nParam stability across folds:")
    for f in res["folds"]:
        print(f"  fold {f['fold']} test {f['test']}: {f['params']}")
