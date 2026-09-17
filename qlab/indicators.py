"""Technical indicators — pure pandas/numpy, no TA-lib dependency.

Every function takes/returns pandas objects aligned to the price index.
`enrich(df)` adds a standard indicator column set used by the strategies.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    roll_down = down.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(s, fast) - ema(s, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(s: pd.Series, n: int = 20, k: float = 2.0):
    mid = sma(s, n)
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    upper, lower = mid + k * sd, mid - k * sd
    pctb = (s - lower) / (upper - lower).replace(0, np.nan)
    bandwidth = (upper - lower) / mid.replace(0, np.nan)
    return mid, upper, lower, pctb, bandwidth


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(df: pd.DataFrame, n: int = 14):
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(df)
    atr_n = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_line = dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return adx_line, plus_di, minus_di


def roc(s: pd.Series, n: int) -> pd.Series:
    return s.pct_change(n) * 100


def donchian(df: pd.DataFrame, n: int = 20):
    hi = df["high"].rolling(n, min_periods=n).max()
    lo = df["low"].rolling(n, min_periods=n).min()
    return hi, lo


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the standard indicator set. Uses adjusted close for signals."""
    out = df.copy()
    # Put OHLC on the same adjusted basis as adjclose, so stops/targets computed
    # from adjusted prices are compared against adjusted highs/lows (no split/div bias).
    factor = (out["adjclose"] / out["close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    out["adj_open"] = out["open"] * factor
    out["adj_high"] = out["high"] * factor
    out["adj_low"] = out["low"] * factor
    px = out["adjclose"]
    out["ret"] = px.pct_change()
    out["ema20"] = ema(px, 20)
    out["ema50"] = ema(px, 50)
    out["sma50"] = sma(px, 50)
    out["sma200"] = sma(px, 200)
    out["rsi14"] = rsi(px, 14)
    out["rsi2"] = rsi(px, 2)
    m, sig, hist = macd(px)
    out["macd"], out["macd_sig"], out["macd_hist"] = m, sig, hist
    mid, up, lo, pctb, bw = bollinger(px, 20, 2.0)
    out["bb_mid"], out["bb_up"], out["bb_lo"], out["bb_pctb"], out["bb_bw"] = mid, up, lo, pctb, bw
    out["atr14"] = atr(out, 14)
    adx_line, pdi, mdi = adx(out, 14)
    out["adx14"], out["plus_di"], out["minus_di"] = adx_line, pdi, mdi
    out["roc63"] = roc(px, 63)
    out["roc126"] = roc(px, 126)
    dc_hi, dc_lo = donchian(out, 20)
    out["dc_hi20"], out["dc_lo20"] = dc_hi.shift(1), dc_lo.shift(1)  # prior-N to avoid lookahead
    out["vol20"] = out["ret"].rolling(20, min_periods=20).std() * np.sqrt(252)
    out["volsma20"] = out["volume"].rolling(20, min_periods=20).mean()
    return out


if __name__ == "__main__":
    from qlab import data as D
    cfg = D.load_config()
    df = D.get_history(cfg["universe"][0], rng=cfg["data"]["backtest_range"])
    e = enrich(df)
    cols = ["adjclose", "ema20", "ema50", "rsi14", "rsi2", "macd_hist", "bb_pctb", "atr14", "adx14", "roc126"]
    print(cfg["universe"][0])
    print(e[cols].tail(6).round(2).to_string())
