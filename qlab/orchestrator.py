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


def _run_livebook(cfg_book: dict, name: str, panel, regime, rfactor, cal, persist=True, state=None, tax_sync=None, tax_inventory=None) -> dict:
    """Advance a realistic live book (next-open fills, T+1 settlement, per-trade costs)."""
    RUNS.mkdir(parents=True, exist_ok=True)
    state_path = RUNS / f"livebook_{name}.json"
    if state is None:
        state = json.loads(state_path.read_text()) if state_path.exists() else LB.new_livebook(cfg_book, name)

    back = cfg_book["paper"]["inception_days_back"]
    inc_idx = len(cal) - 1 if not back else max(260, len(cal) - back)
    inception = cal[min(inc_idx, len(cal) - 1)]
    pt = state.get("processed_through")
    todo = [d for d in cal if d > pd.Timestamp(pt)] if pt else [d for d in cal if d >= inception]
    for date in todo:
        if regime is None or date not in regime.index or pd.isna(regime.loc[date]):
            raise ValueError(f'Missing market regime for {date}')
        if rfactor is None or date not in rfactor.index or pd.isna(rfactor.loc[date]):
            raise ValueError(f'Missing allocation regime for {date}')
        rok = bool(regime.loc[date]); rf = float(rfactor.loc[date])
        if tax_sync is None: LB.step(state, panel, date, cfg_book, rok, rf)
        else: LB.step(state, panel, date, cfg_book, rok, rf, tax_sync=tax_sync,tax_inventory=tax_inventory)
    state["processed_through"] = str(todo[-1].date()) if todo else pt
    if persist:
        _save_book(name, state)
    return {"name": name, "state": state, "capital": cfg_book["starting_capital"],
            "prices_now": E._prices_at(panel, cal[-1])}


def _save_book(name, state, runs=None):
    from dhruva.ledger import atomic_write
    runs=Path(runs) if runs is not None else RUNS
    atomic_write(runs / f"livebook_{name}.json", json.dumps(state, indent=2, default=str).encode('utf-8'))
    orders = {"as_of": state["as_of"], "orders": [o for o in state["orders"]
              if o["status"] == "scheduled" or o.get("fill_date") == state["as_of"]]}
    atomic_write(runs / f"today_orders_{name}.json", json.dumps(orders, indent=2).encode('utf-8'))


def daily_run(refresh: bool = True, verbose: bool = True, progress=None) -> dict:
    emit = progress or (lambda *args: None)
    emit('archive','RUNNING')
    from dhruva.freeze import verify_v1
    verify_v1()  # Original archive integrity; active in-place repairs are authorized.
    emit('archive','COMPLETE')
    cfg = D.load_config()
    book_defs = cfg.get("books") or {"main": {"capital": cfg["starting_capital"], "overrides": {}}}
    input_states = {}
    for name in book_defs:
        path = RUNS / f'livebook_{name}.json'
        input_states[name] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if verbose:
        print("Refreshing data ..." if refresh else "Loading cached data ...")
    emit('data_ingestion','RUNNING')
    if refresh:
        raw = D.update_universe(cfg["universe"], update_range=cfg["data"]["update_range"], clean=False)
        bench_raw = D.update_history(cfg["regime"]["benchmark"], update_range=cfg["data"]["update_range"], clean=False)
    else:
        raw = D.get_universe(cfg["universe"], rng=cfg["data"]["backtest_range"], clean=False)
        bench_raw = D.get_history(cfg["regime"]["benchmark"], rng=cfg["data"]["backtest_range"], clean=False)

    from dhruva.data_quality import validate_inputs
    emit('data_ingestion','COMPLETE', {'returned_symbols':len(raw)})
    emit('data_validation','RUNNING')
    valid, bench_valid, quality = validate_inputs(raw, bench_raw, cfg, input_states, PROJECT_ROOT)
    emit('data_validation','COMPLETE', {'status':quality['status'], 'excluded':quality['excluded'], 'coverage':quality['coverage']})
    emit('features','RUNNING')
    panel = E.build_panel(valid, cfg)
    bench_e = I.enrich(bench_valid)
    regime = E.regime_series(cfg, bench_e)
    rfactor = E.regime_factor_series(cfg, bench_e)
    cal = bench_valid.index.intersection(E.trading_calendar(panel)).sort_values()
    if not len(cal):
        raise ValueError('No benchmark-aligned trading sessions')
    emit('features','COMPLETE')
    emit('benchmark','COMPLETE', {'latest_date':str(cal[-1].date())})

    book_defs = cfg.get("books") or {"main": {"capital": cfg["starting_capital"], "overrides": {}}}
    import copy
    from dhruva.ledger import Ledger
    from dhruva.evidence import record_evaluation
    ledger = Ledger(PROJECT_ROOT/'runs/ledger/dhruva_v1')
    emit('ledger','RUNNING')
    ledger.verify()  # corrupt committed evidence must never be silently bypassed
    states = {}; configs = {}; regimes = {}; factors = {}
    for name, bk in book_defs.items():
        state_path = RUNS / f"livebook_{name}.json"
        states[name] = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else None
        cfg_book = _apply(cfg, bk.get("overrides", {}))
        # Taxonomy must not change when a book overrides its allocation basket.
        cfg_book['excluded_momentum_assets'] = list(cfg.get('defensive_basket', {}))
        cfg_book["starting_capital"] = bk["capital"]
        configs[name] = cfg_book
        regimes[name] = E.regime_series(cfg_book, bench_e)
        factors[name] = E.regime_factor_series(cfg_book, bench_e)
    # Recover a ledger commit that preceded a failed projection write. Only
    # advance projections to existing evidence; never recalculate its decisions.
    segments = sorted((ledger.root/'segments').glob('*.json'))
    if segments:
        last = json.loads(segments[-1].read_text(encoding='utf-8'))['payload']['state']
        for captured in last['results']:
            name = captured['name']; current = states.get(name)
            if name in configs and (not current or (current.get('processed_through') or '') <= captured['state']['as_of']):
                states[name] = copy.deepcopy(captured['state'])
    pending = set()
    checkpoints = {(s or {}).get('processed_through') for s in states.values()}
    if len(checkpoints) != 1:
        raise ValueError('Books have inconsistent checkpoints without a recoverable ledger bundle')
    for name, state in states.items():
        pt = (state or {}).get('processed_through')
        if pt:
            if pd.Timestamp(pt) > cal[-1]: raise ValueError('Portfolio is ahead of available benchmark data')
            pending.update(d for d in cal if d > pd.Timestamp(pt))
        else:
            back = configs[name]['paper']['inception_days_back']
            start = max(260, len(cal)-back) if back else len(cal)-1
            pending.update(cal[min(start, len(cal)-1):])
    dates = sorted(pending) or [cal[-1]]
    results = []
    new_evaluations = 0
    emit('portfolio_engine','RUNNING')
    emit('risk_engine','RUNNING')
    for date in dates:
        previous = copy.deepcopy(states)
        for name in states:
            if states[name] is None: states[name]=LB.new_livebook(configs[name],name)
        inventories=[st.get('account_tax_inventory',{}) for st in states.values()]
        if any(inv!=inventories[0] for inv in inventories):
            raise ValueError('Shared tax inventory differs between book projections')
        tax_inventory=copy.deepcopy(inventories[0])
        from qlab.tax import reserve_accounts
        def sync_tax(): reserve_accounts(states,cfg)
        for st in states.values():
            for symbol in (st or {}).get('holdings', {}):
                if symbol not in panel or date not in panel[symbol].index:
                    raise ValueError(f'Held-symbol valuation missing: {symbol} {date}')
            for order in (st or {}).get('orders', []):
                if order['status']=='scheduled' and order['side']=='BUY' and order['symbol'] not in valid:
                    order.update(status='cancelled', reason='Data quality exclusion; no fill attempted', cancelled_date=str(date.date()))
        results = [_run_livebook(configs[name], name, panel, regimes[name], factors[name],
                    pd.DatetimeIndex([date]), persist=False, state=states[name],tax_sync=sync_tax,
                    tax_inventory=tax_inventory) for name in book_defs]
        sync_tax()
        for r in results:
            r['state']['account_tax_inventory']=copy.deepcopy(tax_inventory)
            # Later book sales can change the shared reserve attribution.
            r['state']['history'][-1][1]=round(LB.total_value(r['state'],r['prices_now']),2)
        if all(r['state'].get('accounting_schema')==2 for r in results):
            from qlab.accounting import verify
            verify(results,cfg)
        # Recovery is recorded at today's actual timestamp, not fabricated as
        # an original live evaluation on the missed date. Snapshots stop at cutoff.
        results, added = record_evaluation(PROJECT_ROOT, cfg,
            {s: f.loc[:date] for s,f in raw.items()}, bench_raw.loc[:date], panel,
            results, previous, recovered=date < cal[-1], quality=quality)
        new_evaluations += int(added)
        for result in results:
            states[result['name']] = result['state']
            _save_book(result['name'], result['state'])
    emit('portfolio_engine','COMPLETE', {'new_evaluations':new_evaluations, 'accounting':'KNOWN_LIMITATIONS'})
    emit('risk_engine','WARNING', 'Existing deterministic risk rules executed; execution/accounting repairs pending')
    emit('ledger','COMPLETE', ledger.verify())

    from qlab import narrator as NR
    from qlab import notify as NT
    emit('report','RUNNING')
    narrative = NR.narrate(cfg, results)
    (RUNS / "narrative.txt").write_text(narrative, encoding="utf-8")
    out = R.build_multi_dashboard(cfg, results, bench_e["adjclose"], narrative=narrative)

    # alert summary (the scheduler can email / Telegram / Discord this)
    alines = [f"Dhruva PAPER ONLY — {results[0]['state'].get('as_of', '')} — simulated next-open intents:"]
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
        alines = [f"Dhruva PAPER ONLY — {results[0]['state'].get('as_of', '')}: NO ACTION — strategy unchanged."]
    (RUNS / "alert.txt").write_text("\n".join(alines), encoding="utf-8")
    emit('report','COMPLETE', str(out))
    import os
    if os.getenv('TELEGRAM_TOKEN') and os.getenv('TELEGRAM_CHAT'):
        emit('alerts','RUNNING')
        delivered=NT.send_telegram(narrative + "\n\n" + "\n".join(alines))
        emit('alerts','COMPLETE' if delivered else 'WARNING', 'Telegram delivered' if delivered else 'Telegram delivery failed')
    else: emit('alerts','NOT_CONFIGURED', 'Optional Telegram is not configured; external failure channel pending Phase9')

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
    return {"results": results, "dashboard": str(out), "data_quality": quality,
            'new_evaluations':new_evaluations,
            'decision_status':'PAPER_INTENTS_PENDING' if any_action else 'NO_ACTION'}


if __name__ == "__main__":
    from dhruva.run_daily import main
    main()
