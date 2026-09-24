"""Independent read-only check; does not fetch prices or advance the strategy."""
from datetime import datetime, timedelta, time
import json
from pathlib import Path

from dhruva.calendar import IST, expected_date
from dhruva.health import inspect
from dhruva.ledger import atomic_write, canonical, utc_now

ROOT=Path(__file__).resolve().parents[1]


def evaluate(root=ROOT, now=None):
    now=now or datetime.now(IST)
    health=inspect(root, now)
    # Main job nominal18:30; permit delayed dispatch through00:30 next day.
    # At other times check the preceding completed deadline, never today's
    # still-not-due job. Data validation failures are immediately actionable.
    deadline_day=now.date()-timedelta(days=1)
    if now.time()<time(0,30): deadline_day-=timedelta(days=1)
    reference=datetime.combine(deadline_day,time(18,30),tzinfo=IST)
    try: expected=expected_date(reference)
    except ValueError as exc:
        expected=None; health['problems'].append(str(exc))
    errors=[p for p in health['problems'] if ' STALE:' not in p]
    for field in ('market_date','portfolio_date'):
        if expected and (not health[field] or health[field]<expected):
            errors.append(f'{field} stale/missing: {health[field]}; required {expected}')
    success=health.get('last_success') or {}
    if expected and (success.get('market_date') or '')<expected:
        errors.append('MISSED_RUN: no completed attempt for '+expected)
    ledger=health.get('ledger') or {}
    if not ledger.get('events'): errors.append('LEDGER_HEARTBEAT_MISSING')
    return dict(observed_at=utc_now(),status='FAILED' if errors else 'PASS',
                required_session=expected, last_completed_run=success.get('run_id'),
                market_date=health['market_date'],portfolio_date=health['portfolio_date'],
                ledger_head=ledger.get('head'),errors=errors,
                warnings=health['warnings'],scope='Operational liveness only; not accounting certification')


def main():
    result=evaluate()
    atomic_write(ROOT/'runs/watchdog/latest.json',canonical(result)+b'\n')
    print(json.dumps(result,indent=2))
    return 1 if result['errors'] else 0


if __name__=='__main__': raise SystemExit(main())
