"""Daily orchestrator — the live paper-trading loop.

Supports one or more "books" (config.books): each is the same engine with its own
config overrides, capital, and persisted state (runs/livebook_<name>.json), so you can
run e.g. an aggressive book and a balanced book side by side. Shared market data is
loaded once. Safe to re-run (idempotent per day).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from qlab import data as D
from qlab import indicators as I
from qlab import engine as E
from qlab import metrics as M
from qlab import learn as L
from qlab import report as R
from qlab import livebook as LB
from qlab.optimize import _apply

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS = PROJECT_ROOT / "runs"


def _run_livebook(cfg_book: dict, name: str, panel, regime, rfactor, cal, persist=True) -> dict:
    """Advance a realistic live book (next-open fills, T+1 settlement, per-trade costs)."""
    RUNS.mkdir(parents=True, exist_ok=True)
    state_path = RUNS / f"livebook_{name}.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else LB.new_livebook(cfg_book, name)

    back = cfg_book["paper"]["inception_days_back"]
    inc_idx = len(cal) - 1 if not back else max(260, len(cal) - back)
    inception = cal[min(inc_idx, len(cal) - 1)]
    pt = state.get("processed_through")
    todo = [d for d in cal if d >= inception and (pt is None or d > pd.Timestamp(pt))]
    for date in todo:
        rok = True if regime is None else bool(regime.get(date, True))
        rf = 1.0 if rfactor is None else float(rfactor.get(date, 1.0))
        LB.step(state, panel, date, cfg_book, rok, rf)
    state["processed_through"] = str(todo[-1].date()) if todo else pt
    if persist:
        _save_book(name, state)
    return {"name": name, "state": state, "capital": cfg_book["starting_capital"],
            "prices_now": E._prices_at(panel, cal[-1])}


def _save_book(name, state):
    from dhruva.ledger import atomic_write
    atomic_write(RUNS / f"livebook_{name}.json", json.dumps(state, indent=2, default=str).encode('utf-8'))
    orders = {"as_of": state["as_of"], "orders": [o for o in state["orders"]
              if o["status"] == "scheduled" or o.get("fill_date") == state["as_of"]]}
    atomic_write(RUNS / f"today_orders_{name}.json", json.dumps(orders, indent=2).encode('utf-8'))


def daily_run(refresh: bool = True, verbose: bool = True) -> dict:
    from dhruva.freeze import verify_v1
    verify_v1()  # reject unversioned economic changes before data or state writes
    cfg = D.load_config()
    if verbose:
        print("Refreshing data ..." if refresh else "Loading cached data ...")
    if refresh:
        raw = D.update_universe(cfg["universe"], update_range=cfg["data"]["update_range"])
        bench_raw = D.update_history(cfg["regime"]["benchmark"], update_range=cfg["data"]["update_range"])
    else:
        raw = D.get_universe(cfg["universe"], rng=cfg["data"]["backtest_range"])
        bench_raw = D.get_history(cfg["regime"]["benchmark"], rng=cfg["data"]["backtest_range"])

    panel = E.build_panel(raw, cfg)
    bench_e = I.enrich(bench_raw)
    regime = E.regime_series(cfg, bench_e)
    rfactor = E.regime_factor_series(cfg, bench_e)
    cal = E.trading_calendar(panel)

    book_defs = cfg.get("books") or {"main": {"capital": cfg["starting_capital"], "overrides": {}}}
    results = []
    previous = {}
    for name, bk in book_defs.items():
        state_path = RUNS / f"livebook_{name}.json"
        previous[name] = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        cfg_book = _apply(cfg, bk.get("overrides", {}))
        cfg_book["starting_capital"] = bk["capital"]
        rg = E.regime_series(cfg_book, bench_e)
        rf = E.regime_factor_series(cfg_book, bench_e)
        results.append(_run_livebook(cfg_book, name, panel, rg, rf, cal, persist=False))

    from dhruva.evidence import record_evaluation
    results, _ = record_evaluation(PROJECT_ROOT, cfg, raw, bench_raw, panel, results, previous)
    # Ledger contains both books before mutable projections are published. A
    # repeat restores the first captured same-date bundle, not revised evidence.
    for result in results:
        _save_book(result['name'], result['state'])

    from qlab import narrator as NR
    from qlab import notify as NT
    narrative = NR.narrate(cfg, results)
    (RUNS / "narrative.txt").write_text(narrative, encoding="utf-8")
    out = R.build_multi_dashboard(cfg, results, bench_e["adjclose"], narrative=narrative)

    # alert summary (the scheduler can email / Telegram / Discord this)
    alines = [f"Dhruva — {results[0]['state'].get('as_of', '')} — place these at the next market open:"]
    any_action = False
    for r in results:
        sched = [o for o in r["state"]["orders"] if o["status"] == "scheduled"]
        if not sched:
            continue
        any_action = True
        alines.append(f"[{r['name']}]")
        for o in sched:
            if o["side"] == "BUY":
                alines.append(f"  BUY {o['symbol'].replace('.NS', '')} ~{cfg['base_currency']}{o.get('target_value', 0):,.0f}")
            else:
                alines.append(f"  SELL {o['symbol'].replace('.NS', '')} ({o.get('reason', '')})")
    if not any_action:
        alines = [f"Dhruva — {results[0]['state'].get('as_of', '')}: no action today, hold your positions."]
    (RUNS / "alert.txt").write_text("\n".join(alines), encoding="utf-8")
    NT.send_telegram(narrative + "\n\n" + "\n".join(alines))  # no-op unless TELEGRAM_* env set

    if verbose:
        ccy = cfg["base_currency"]
        for r in results:
            st = r["state"]
            val = LB.total_value(st, r["prices_now"])
            sched = [o for o in st["orders"] if o["status"] == "scheduled"]
            print(f"\n=== BOOK: {r['name']} ({ccy}{r['capital']:,.0f}) — Day {st['step_count']} ===")
            print(f"  Value {ccy}{val:,.0f} · cash {ccy}{st['cash']:,.0f} · {len(st['holdings'])} holdings"
                  f" · fees {ccy}{st['charges_total']:,.0f}")
            for o in sched[:8]:
                if o["side"] == "BUY":
                    print(f"    SCHEDULED BUY  {o['symbol']:12s} ~{ccy}{o.get('target_value', 0):,.0f} (fills next open)")
                else:
                    print(f"    SCHEDULED SELL {o['symbol']:12s} ({o.get('reason', '')})")
        print(f"\nDashboard: {out}")
    return {"results": results, "dashboard": str(out)}


if __name__ == "__main__":
    daily_run(refresh=False)
