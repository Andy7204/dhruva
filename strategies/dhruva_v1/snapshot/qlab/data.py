"""Data layer — Yahoo Finance daily bars, cached locally.

Uses only urllib (proven to work through the corporate proxy) + pandas.
Caches each symbol to data/cache/<sym>.csv so history accumulates and we never
re-download what we already have.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]

OHLCV = ["open", "high", "low", "close", "adjclose", "volume"]


def load_config() -> dict:
    with open(PROJECT_ROOT / "config.json", "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    # optionally load the universe from a file (keeps 500 tickers out of config)
    uf = cfg.get("universe_file")
    if uf:
        p = PROJECT_ROOT / uf
        if p.exists():
            cfg["universe"] = [s.strip() for s in p.read_text().splitlines() if s.strip()]
    # ensure the defensive basket assets are fetched + in the panel
    for da in list((cfg.get("defensive_basket") or {}).keys()) + ([cfg["defensive_asset"]] if cfg.get("defensive_asset") else []):
        if da and da not in cfg.get("universe", []):
            cfg.setdefault("universe", []).append(da)
    return cfg


def _safe_name(symbol: str) -> str:
    return symbol.replace("^", "_IDX_").replace(".", "_").replace("=", "_")


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{_safe_name(symbol)}.csv"


def fetch_yahoo(symbol: str, rng: str = "5y", interval: str = "1d",
                retries: int = 3) -> pd.DataFrame:
    """Fetch OHLCV from Yahoo's chart API. Returns a date-indexed DataFrame."""
    params = f"?range={rng}&interval={interval}&events=div%2Csplit"
    last_err = None
    for attempt in range(retries):
        host = _HOSTS[attempt % len(_HOSTS)]
        url = f"{host}/v8/finance/chart/{urllib.parse.quote(symbol, safe='')}{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            raw = urllib.request.urlopen(req, timeout=30).read()
            payload = json.loads(raw)
            result = payload["chart"]["result"]
            if not result:
                raise ValueError("empty result")
            r = result[0]
            ts = r.get("timestamp")
            if not ts:
                return pd.DataFrame(columns=OHLCV)
            q = r["indicators"]["quote"][0]
            adj = (r["indicators"].get("adjclose") or [{}])[0].get("adjclose")
            df = pd.DataFrame({
                "open": q.get("open"),
                "high": q.get("high"),
                "low": q.get("low"),
                "close": q.get("close"),
                "adjclose": adj if adj is not None else q.get("close"),
                "volume": q.get("volume"),
            }, index=pd.to_datetime(pd.Series(ts, dtype="int64"), unit="s"))
            df.index = df.index.normalize()
            df.index.name = "date"
            df = df[~df["close"].isna()].copy()
            df = df[~df.index.duplicated(keep="last")]
            return df
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
            last_err = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"fetch failed for {symbol}: {last_err}")


def clean_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Drop corrupt price ticks: non-positive prices and isolated spikes that
    deviate >50% from the local (centered 5-day) median. Circuit limits cap real
    Indian daily moves near ±20%, so a 50% deviation is almost always bad data."""
    if df is None or df.empty:
        return df
    df = df[(df["close"] > 0) & (df["adjclose"] > 0)].copy()
    med = df["adjclose"].rolling(5, center=True, min_periods=3).median()
    ratio = df["adjclose"] / med
    good = ratio.between(0.5, 1.5) | med.isna()
    return df[good]


def _read_cache(symbol: str) -> pd.DataFrame | None:
    p = _cache_path(symbol)
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"], index_col="date")
    return df


def _write_cache(symbol: str, df: pd.DataFrame) -> None:
    df.sort_index().to_csv(_cache_path(symbol))


def get_history(symbol: str, rng: str = "5y", interval: str = "1d",
                refresh: bool = False) -> pd.DataFrame:
    """Return cached history, fetching if absent or refresh=True."""
    if not refresh:
        cached = _read_cache(symbol)
        if cached is not None and len(cached) > 5:
            return clean_ohlc(cached)
    df = fetch_yahoo(symbol, rng=rng, interval=interval)
    _write_cache(symbol, df)
    return clean_ohlc(df)


def update_history(symbol: str, update_range: str = "3mo",
                   interval: str = "1d") -> pd.DataFrame:
    """Fetch recent bars and merge into the cache (cache wins on ties=latest)."""
    cached = _read_cache(symbol)
    fresh = fetch_yahoo(symbol, rng=update_range, interval=interval)
    if cached is None:
        merged = fresh
    else:
        merged = pd.concat([cached, fresh])
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    _write_cache(symbol, merged)
    return clean_ohlc(merged)


def get_universe(symbols: list[str], rng: str = "5y", interval: str = "1d",
                 refresh: bool = False, pause: float = 0.4) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for i, sym in enumerate(symbols):
        was_cached = _cache_path(sym).exists() and not refresh
        try:
            out[sym] = get_history(sym, rng=rng, interval=interval, refresh=refresh)
        except Exception as exc:  # noqa: BLE001 - keep going, report per symbol
            print(f"  ! {sym}: {exc}")
        if pause and not was_cached and i < len(symbols) - 1:
            time.sleep(pause)  # only throttle real network fetches, not cache reads
    return out


def update_universe(symbols: list[str], update_range: str = "3mo",
                    interval: str = "1d", pause: float = 0.4) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for i, sym in enumerate(symbols):
        try:
            out[sym] = update_history(sym, update_range=update_range, interval=interval)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {sym}: {exc}")
            cached = _read_cache(sym)
            if cached is not None:
                out[sym] = cached
        if pause and i < len(symbols) - 1:
            time.sleep(pause)
    return out


if __name__ == "__main__":
    cfg = load_config()
    print(f"Fetching {len(cfg['universe'])} symbols (range={cfg['data']['backtest_range']}) ...")
    data = get_universe(cfg["universe"], rng=cfg["data"]["backtest_range"])
    for s, d in data.items():
        print(f"  {s:14s} rows={len(d):5d}  {d.index.min().date()} -> {d.index.max().date()}  last={d['close'].iloc[-1]:.2f}")
