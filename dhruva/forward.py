"""Forward paper books for the chosen v2 strategies.

Each run replays every book deterministically from the forward start date with
the same engine used in research (one-session execution lag, ETF costs, Indian
tax, liquidation value). Each completed session is appended once to
runs/forward/log.jsonl with its generation time; earlier rows are never
rewritten. If a replay later disagrees with a saved row (for example after a
vendor revision), the disagreement is recorded as a warning, not hidden.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from lab import engine as E, strategies as S

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT/'runs'/'forward'


def config(root=ROOT):
    return json.loads((Path(root)/'config.v2.json').read_text(encoding='utf-8'))


def replay(cfg, prices=None, through=None):
    """Return {book_id: summary} for every book plus the benchmark, through `through`."""
    prices = prices if prices is not None else E.load()
    if through: prices = prices.loc[:pd.Timestamp(through)]
    cal = prices.index
    start = cal.get_indexer([pd.Timestamp(cfg['forward_start'])], method='bfill')[0]
    if start < 0 or start >= len(cal):
        return {}
    end = len(cal)-1
    books = dict(cfg['books']); books['N50'] = {'strategy': cfg['benchmark'], 'label': 'Nifty 50 buy and hold (benchmark)'}
    out = {}
    for bid, spec in books.items():
        strat = S.CANDIDATES[spec['strategy']](); strat.start = start
        curve, acct, log = E.run(prices, strat, start, end, capital=cfg['capital'], liq_every=1)
        px = prices.iloc[end]
        held = {a: sum(l.qty for l in ls)*px[a] for a, ls in acct.lots.items()}
        value = acct.cash+sum(held.values())
        pending = log[-1][1] if log and log[-1][0] == cal[end] else None
        out[bid] = {'label': spec['label'], 'strategy': spec['strategy'],
                    'as_of': str(cal[end].date()), 'nav': round(float(curve['nav'].iloc[-1]), 2),
                    'liquidation_value': round(float(curve['liq'].iloc[-1]), 2),
                    'weights': {a: round(float(v/value), 4) for a, v in sorted(held.items())},
                    'cash_weight': round(float(acct.cash/value), 4),
                    'next_review_in': int(strat.every-(end-start) % strat.every) if strat.every else None,
                    'pending_target': pending, 'last_decision': str(log[-1][0].date()) if log else None,
                    'last_target': log[-1][1] if log else None,
                    'tax_paid': round(acct.tax_paid, 2), 'costs': round(acct.costs, 2), 'trades': acct.trades,
                    'curve': [[str(d.date()), round(float(n), 2), round(float(l), 2)]
                              for d, n, l in zip(curve.index, curve['nav'], curve['liq'])]}
    return out


def record(books, root=ROOT, now=None):
    """Append one row per book for the latest session; never rewrite. Returns warnings."""
    folder = Path(root)/'runs'/'forward'; folder.mkdir(parents=True, exist_ok=True)
    log = folder/'log.jsonl'
    saved = [json.loads(x) for x in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
    seen = {(r['book'], r['date']): r for r in saved}
    now = now or datetime.now(timezone.utc).isoformat()
    warnings, rows = [], []
    for bid, b in books.items():
        for date, nav, liq in b['curve']:
            prior = seen.get((bid, date))
            if prior:
                if abs(prior['liquidation_value']/liq-1) > 1e-4:
                    warnings.append(f'{bid} {date}: replay {liq:,.2f} differs from recorded {prior["liquidation_value"]:,.2f}')
            elif date == b['as_of']:
                rows.append({'book': bid, 'date': date, 'nav': nav, 'liquidation_value': liq,
                             'weights': b['weights'], 'pending_target': b['pending_target'], 'recorded_at': now})
            else:
                rows.append({'book': bid, 'date': date, 'nav': nav, 'liquidation_value': liq,
                             'recorded_at': now, 'reconstructed': True})
    # Serialize everything first so a failure cannot leave a half-written record.
    state = json.dumps({k: {x: y for x, y in v.items() if x != 'curve'} for k, v in books.items()}, indent=1, sort_keys=True)
    lines = ''.join(json.dumps(r, sort_keys=True)+'\n' for r in rows)
    if lines:
        with log.open('a', encoding='utf-8') as stream: stream.write(lines)
    (folder/'state.json').write_text(state, encoding='utf-8')
    return warnings


def history(root=ROOT):
    """Recorded rows as a frame: date x book liquidation value (first recording wins)."""
    log = Path(root)/'runs'/'forward'/'log.jsonl'
    if not log.exists(): return pd.DataFrame()
    rows = [json.loads(x) for x in log.read_text(encoding='utf-8').splitlines()]
    frame = pd.DataFrame(rows).drop_duplicates(['book', 'date'], keep='first')
    return frame.pivot(index='date', columns='book', values='liquidation_value').sort_index()
