"""Performance metrics for an equity curve + closed-trade list."""
from __future__ import annotations

import numpy as np
import pandas as pd

PPY = 252  # trading periods per year


def max_drawdown(equity: pd.Series) -> tuple[float, pd.Timestamp | None]:
    if len(equity) < 2:
        return 0.0, None
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    trough = dd.idxmin()
    return float(dd.min()), trough


def compute_metrics(equity: pd.Series, closed_trades: list[dict], ppy: int = PPY) -> dict:
    equity = pd.Series(equity).dropna()
    out: dict = {"final_equity": float(equity.iloc[-1]) if len(equity) else 0.0}
    if len(equity) < 3:
        out.update({"total_return_pct": 0.0, "cagr_pct": 0.0, "ann_vol_pct": 0.0,
                    "sharpe": 0.0, "sortino": 0.0, "max_drawdown_pct": 0.0, "calmar": 0.0})
    else:
        rets = equity.pct_change().dropna()
        start, end = float(equity.iloc[0]), float(equity.iloc[-1])
        years = max(len(equity) / ppy, 1e-9)
        total_return = end / start - 1.0
        cagr = (end / start) ** (1 / years) - 1.0 if start > 0 else 0.0
        ann_vol = float(rets.std(ddof=0) * np.sqrt(ppy))
        mean_ann = float(rets.mean() * ppy)
        sharpe = mean_ann / ann_vol if ann_vol > 1e-12 else 0.0
        # standard downside deviation: RMS of below-target (0) returns over ALL periods
        neg = np.minimum(rets.to_numpy(), 0.0)
        dd_vol = float(np.sqrt((neg ** 2).mean()) * np.sqrt(ppy))
        sortino = mean_ann / dd_vol if dd_vol > 1e-12 else 0.0
        mdd, _ = max_drawdown(equity)
        out.update({
            "total_return_pct": round(total_return * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "ann_vol_pct": round(ann_vol * 100, 2),
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "max_drawdown_pct": round(mdd * 100, 2),
            "calmar": round(cagr / abs(mdd), 2) if mdd < -1e-9 else 0.0,
        })

    n = len(closed_trades)
    if n:
        pnls = np.array([t["net_pnl"] for t in closed_trades], dtype=float)
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        gross_win = float(wins.sum())
        gross_loss = float(-losses.sum())
        holds = [t.get("hold_days", 0) for t in closed_trades]
        out.update({
            "num_trades": n,
            "win_rate_pct": round(len(wins) / n * 100, 1),
            "avg_win": round(float(wins.mean()), 1) if len(wins) else 0.0,
            "avg_loss": round(float(losses.mean()), 1) if len(losses) else 0.0,
            "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 1e-9 else 999.0,
            "expectancy": round(float(pnls.mean()), 1),
            "total_net_pnl": round(float(pnls.sum()), 1),
            "avg_hold_days": round(float(np.mean(holds)), 1) if holds else 0.0,
            "total_charges": round(sum(t.get("charges", 0.0) for t in closed_trades), 1),
        })
    else:
        out.update({"num_trades": 0, "win_rate_pct": 0.0, "profit_factor": 0.0,
                    "expectancy": 0.0, "total_net_pnl": 0.0, "avg_hold_days": 0.0,
                    "total_charges": 0.0})
    return out


def per_strategy_expectancy(closed_trades: list[dict]) -> dict:
    """Expectancy + win-rate grouped by (sleeve, strategy) — the learning signal."""
    groups: dict[tuple, list] = {}
    for t in closed_trades:
        key = (t.get("sleeve", "?"), t.get("strategy", "?"))
        groups.setdefault(key, []).append(t["net_pnl"])
    res = {}
    for (sleeve, strat), pnls in groups.items():
        arr = np.array(pnls, dtype=float)
        wins = (arr > 0).sum()
        res[f"{sleeve}/{strat}"] = {
            "trades": len(arr),
            "win_rate_pct": round(wins / len(arr) * 100, 1),
            "expectancy": round(float(arr.mean()), 1),
            "total_pnl": round(float(arr.sum()), 1),
        }
    return res
