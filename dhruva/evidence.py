"""Capture original v1 evaluations without changing its trading decisions.

Legacy imports are identified explicitly; they are not timestamped forward calls.
Original archive evidence is retained while authorized repairs proceed in place.
"""
import copy
import json
import math
import subprocess
from pathlib import Path

import pandas as pd

from dhruva.ledger import Ledger, digest, utc_now


def scalar(value):
    if value is None or pd.isna(value): return None
    return float(value)


def frame_snapshot(frame):
    return {'columns': list(frame.columns), 'dates': [str(x) for x in frame.index],
            'rows': [[scalar(v) for v in row] for row in frame.itertuples(index=False, name=None)]}


def record_evaluation(root, cfg, raw, benchmark, panel, results, previous, *, generated_at=None, recovered=False):
    root = Path(root)
    ledger = Ledger(root/'runs/ledger/dhruva_v1')
    as_of = max(r['state']['as_of'] for r in results)
    key = f'dhruva-v1:{as_of}'
    prior = ledger.find(key)
    if prior:
        # Same-day repeated fetches must not replace the first recorded evidence.
        return prior['payload']['state']['results'], False
    generated_at = generated_at or utc_now()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    snapshot = ledger.snapshot({'config': cfg, 'market': {s: frame_snapshot(f) for s, f in sorted(raw.items())},
                                'benchmark': frame_snapshot(benchmark),
                                'fetched_at': generated_at, 'price_convention': 'legacy adjusted OHLC'})
    names_path = root/'data/nse_names.json'
    names = json.loads(names_path.read_text(encoding='utf-8')) if names_path.exists() else {}
    events = []
    date = pd.Timestamp(as_of)
    bench_level = scalar(benchmark.at[date, 'adjclose']) if date in benchmark.index else None
    for result in results:
        state = result['state']; book = result['name']; prev = previous.get(book) or {}
        legacy = prev.get('as_of') == state['as_of']
        nav = state['history'][-1][1] if state['history'] else state['capital']
        previous_nav = (prev.get('history') or [[None, prev.get('capital', state['capital'])]])[-1][1]
        prices = result['prices_now']
        orders = [o for o in state['orders'] if o.get('decided_date') == as_of and o['status'] == 'scheduled']
        by_symbol = {o['symbol']: o for o in orders}
        symbols = sorted(set(panel) | set(state['holdings']) | set(by_symbol))
        for symbol in symbols or [None]:
            holding = state['holdings'].get(symbol, {})
            old = prev.get('holdings', {}).get(symbol, {})
            price = prices.get(symbol)
            weight = holding.get('qty', 0)*(price or 0)/nav if nav else 0
            prior_weight = old.get('qty', 0)*(price or 0)/previous_nav if previous_nav else 0
            order = by_symbol.get(symbol)
            action = 'HOLD' if holding else 'NO_ACTION'
            target = weight
            if order:
                if order['side'] == 'BUY':
                    action = 'INCREASE' if holding else 'BUY'
                    target = weight + order.get('target_value', 0)/nav if nav else None
                else:
                    q = order.get('qty') or holding.get('qty', 0)
                    action = 'REDUCE' if q < holding.get('qty', 0) else 'SELL'
                    target = max(0, weight-q*(price or 0)/nav) if nav else None
            row = panel[symbol].loc[date] if symbol in panel and date in panel[symbol].index else None
            components = {k: scalar(row.get(k)) if row is not None else None
                          for k in ('mom_raw', 'mom_score', 'vol20', 'sma200', 'turnover', 'atr14')}
            components.update(risk_on=state.get('risk_on'), breaker=state.get('breaker', False),
                              book=book, rebalance_in=state.get('next_rebalance_in'))
            events.append(dict(run_id=key, generated_at=generated_at,
                               # Original daily bars have dates, not a verified finalization time.
                               data_cutoff_at=as_of+'T00:00:00+05:30', effective_date=as_of,
                               strategy_id='dhruva_momentum:'+book, strategy_version='1.0', git_commit=commit,
                               configuration_hash=digest(cfg), data_snapshot=snapshot, ticker=symbol,
                               company_name=names.get(symbol, symbol), action=action,
                               previous_weight=prior_weight, target_weight=target,
                               signal_score=components['mom_score'], signal_components=components,
                               market_price=price, rationale=(order or {}).get('reason') or
                               ('Legacy state observed; not a newly timestamped signal' if legacy else
                                'Deterministic paper evaluation; see components and scheduled paper orders'),
                               portfolio_nav=nav, benchmark_level=bench_level, execution_mode='PAPER',
                               execution_status='RECOVERY_RECONSTRUCTION' if recovered else
                               'IMPORTED_LEGACY_OBSERVATION' if legacy else
                               ('SCHEDULED_NEXT_OPEN' if order else 'EVALUATED'),
                               data_cutoff_quality='date-only legacy bar; finalization unverified',
                               weight_basis='marked at captured current price, not historical closing weight',
                               target_weight_quality='pre-cost order intent, not guaranteed filled weight',
                               recovery_reconstruction=recovered,
                               accounting_quality='KNOWN_DEFECTS_UNDER_REPAIR'))
    bundle = {'results': copy.deepcopy(results), 'previous': copy.deepcopy(previous),
              'config': cfg, 'data_snapshot': snapshot, 'legacy_import': all(
                  (previous.get(r['name']) or {}).get('as_of') == r['state']['as_of'] for r in results)}
    envelope, added = ledger.append(key, events, bundle)
    return envelope['payload']['state']['results'], added
