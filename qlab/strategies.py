"""Strategy library — long-only signal generators + per-sleeve ensembles.

Each base strategy takes an enriched frame (see indicators.enrich) and returns a
0/1 desired-exposure Series aligned to the index. Sleeves combine strategies by
weighted vote; the long-term sleeve additionally ranks names cross-sectionally.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ----------------------------- base strategies -----------------------------

def ma_crossover(e: pd.DataFrame, fast: str = "ema20", slow: str = "ema50") -> pd.Series:
    return (e[fast] > e[slow]).astype(float)


def macd_trend(e: pd.DataFrame) -> pd.Series:
    return ((e["macd"] > e["macd_sig"]) & (e["macd_hist"] > 0)).astype(float)


def _state_machine(entry: pd.Series, exit_: pd.Series) -> pd.Series:
    en = entry.fillna(False).to_numpy()
    ex = exit_.fillna(False).to_numpy()
    pos = np.zeros(len(en))
    holding = 0
    for i in range(len(en)):
        if holding == 0 and en[i]:
            holding = 1
        elif holding == 1 and ex[i]:
            holding = 0
        pos[i] = holding
    return pd.Series(pos, index=entry.index)


def donchian_breakout(e: pd.DataFrame, n: int = 20) -> pd.Series:
    entry = e["adjclose"] > e["dc_hi20"]
    exit_ = e["adjclose"] < e["dc_lo20"]
    return _state_machine(entry, exit_)


def rsi2_meanrev(e: pd.DataFrame, entry_lvl: float = 10, exit_lvl: float = 60) -> pd.Series:
    uptrend = e["adjclose"] > e["sma200"]
    entry = uptrend & (e["rsi2"] < entry_lvl)
    exit_ = e["rsi2"] > exit_lvl
    return _state_machine(entry, exit_)


def bollinger_meanrev(e: pd.DataFrame, entry_pctb: float = 0.05, exit_pctb: float = 0.55) -> pd.Series:
    uptrend = e["adjclose"] > e["sma200"]
    entry = uptrend & (e["bb_pctb"] < entry_pctb)
    exit_ = e["bb_pctb"] > exit_pctb
    return _state_machine(entry, exit_)


def trend_filter(e: pd.DataFrame) -> pd.Series:
    """Long-term regime: price above the 200-day and positive 6-month momentum."""
    return ((e["adjclose"] > e["sma200"]) & (e["roc126"] > 0)).astype(float)


# --------------------------- sleeve ensembles ------------------------------

STACKS: dict[str, list[tuple]] = {
    "swing": [(ma_crossover, {}, 1.0), (macd_trend, {}, 1.0), (donchian_breakout, {}, 1.0)],
    "short_term": [(rsi2_meanrev, {}, 1.0), (bollinger_meanrev, {}, 1.0)],
    "long_term": [(trend_filter, {}, 1.0)],
}
THRESHOLD = {"swing": 0.5, "short_term": 0.5, "long_term": 1.0}


def sleeve_score(sleeve: str, e: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """Return a frame with per-strategy 0/1 columns and a weighted 'score' [0,1]."""
    stack = STACKS[sleeve]
    cols = {}
    wsum = 0.0
    score = pd.Series(0.0, index=e.index)
    for fn, kw, base_w in stack:
        name = fn.__name__
        w = base_w * (weights or {}).get(name, 1.0)
        sig = fn(e, **kw)
        cols[name] = sig
        score = score.add(sig * w, fill_value=0.0)
        wsum += w
    score = score / wsum if wsum else score
    out = pd.DataFrame(cols)
    out["score"] = score
    return out


def sleeve_desired(sleeve: str, e: pd.DataFrame, weights: dict | None = None) -> pd.Series:
    sc = sleeve_score(sleeve, e, weights)
    return (sc["score"] >= THRESHOLD[sleeve]).astype(float)


def momentum_rank_value(e: pd.DataFrame) -> float:
    """Scalar momentum score for cross-sectional long-term ranking (latest bar)."""
    row = e.iloc[-1]
    if pd.isna(row.get("roc126")) or pd.isna(row.get("sma200")):
        return float("nan")
    if row["adjclose"] <= row["sma200"]:
        return float("nan")  # only rank names in an uptrend
    vol = row.get("vol20")
    vol = vol if (vol and vol > 0) else np.nan
    # risk-adjusted momentum: 6m return blended with 3m, penalised by volatility
    raw = 0.6 * row["roc126"] + 0.4 * row.get("roc63", 0.0)
    return float(raw / vol) if vol and not np.isnan(vol) else float(raw)


def latest_signal_report(sleeve: str, e: pd.DataFrame, weights: dict | None = None) -> dict:
    """Human-readable signal snapshot for the most recent bar (for journaling)."""
    sc = sleeve_score(sleeve, e, weights)
    last = e.iloc[-1]
    fired = {k: float(sc[k].iloc[-1]) for k in sc.columns if k != "score"}
    return {
        "score": round(float(sc["score"].iloc[-1]), 3),
        "threshold": THRESHOLD[sleeve],
        "strategies_fired": fired,
        "rsi14": round(float(last["rsi14"]), 1),
        "rsi2": round(float(last["rsi2"]), 1),
        "adx14": round(float(last["adx14"]), 1),
        "macd_hist": round(float(last["macd_hist"]), 2),
        "bb_pctb": round(float(last["bb_pctb"]), 2),
        "roc126": round(float(last["roc126"]), 1),
        "above_sma200": bool(last["adjclose"] > last["sma200"]) if not pd.isna(last["sma200"]) else None,
        "atr14": round(float(last["atr14"]), 2),
        "close": round(float(last["adjclose"]), 2),
    }


if __name__ == "__main__":
    from qlab import data as D
    from qlab import indicators as I
    cfg = D.load_config()
    for sym in ["RELIANCE.NS", "TCS.NS", "SBIN.NS"]:
        e = I.enrich(D.get_history(sym, rng=cfg["data"]["backtest_range"]))
        for sleeve in ("swing", "short_term", "long_term"):
            d = sleeve_desired(sleeve, e)
            rep = latest_signal_report(sleeve, e)
            print(f"{sym:12s} {sleeve:11s} desired_now={int(d.iloc[-1])} "
                  f"score={rep['score']} fired={rep['strategies_fired']}")
        print(f"    momentum_rank={momentum_rank_value(e):.3f}")
