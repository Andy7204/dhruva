"""Independent read-only liveness check; never fetches prices or changes books."""
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path

from dhruva.calendar import IST, expected_date
from dhruva.util import atomic_write, canonical, utc_now

ROOT = Path(__file__).resolve().parents[1]


def sessions_behind(recorded, required):
    """Trading sessions after `recorded` up to and including `required`."""
    from dhruva.calendar import is_session
    if not recorded or recorded >= required: return 0
    n, day = 0, date.fromisoformat(recorded)+timedelta(days=1)
    while day <= date.fromisoformat(required):
        try:
            n += is_session(day)
        except ValueError:
            n += day.weekday() < 5
        day += timedelta(days=1)
    return n


def stale(label, recorded, required, errors, warnings):
    """One session behind is normal when a vendor publishes late (the retry run catches up); two or more is an incident."""
    behind = sessions_behind(recorded, required)
    if behind >= 2: errors.append(f'{label} STALE: recorded {recorded}, required {required} ({behind} sessions behind)')
    elif behind == 1: warnings.append(f'{label} one session behind ({recorded}); retry run pending')


def evaluate(root=ROOT, now=None):
    now = now or datetime.now(IST)
    errors, warnings = [], []
    day = now.date()-timedelta(days=1 if now.time() >= time(0, 30) else 2)
    try:
        required = expected_date(datetime.combine(day, time(18, 30), tzinfo=IST))
    except ValueError as exc:
        required = None; errors.append(str(exc))
    try:
        cal = json.loads((Path(root)/'data/trading_calendar.json').read_text(encoding='utf-8'))
        left = (date.fromisoformat(cal['valid_through'])-now.date()).days
        if left <= 3:
            errors.append(f'CALENDAR MAINTENANCE: trading calendar ends {cal["valid_through"]}, {left} days left. Add official NSE dates.')
        elif left <= 14:
            warnings.append(f'Calendar coverage ends {cal["valid_through"]} ({left} days); add official NSE dates.')
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f'CALENDAR UNREADABLE: {exc}')
    try:
        status = json.loads((Path(root)/'runs/status.json').read_text(encoding='utf-8'))
        if status.get('status') == 'FAILED':
            errors.append('LAST DAILY RUN FAILED: '+'; '.join(status.get('errors', [])))
        warnings += status.get('warnings', [])
    except (OSError, ValueError):
        errors.append('DAILY STATUS MISSING')
    try:
        state = json.loads((Path(root)/'runs/forward/state.json').read_text(encoding='utf-8'))
        as_of = min(b['as_of'] for b in state.values())
        if required: stale('BOOKS', as_of, required, errors, warnings)
    except (OSError, ValueError, KeyError):
        cfg = json.loads((Path(root)/'config.v2.json').read_text(encoding='utf-8'))
        if required and required > cfg['forward_start']:
            errors.append('FORWARD BOOKS MISSING')
    try:
        inf = json.loads((Path(root)/'runs/inflection/status.json').read_text(encoding='utf-8'))
        if required: stale('INFLECTION SCAN', inf.get('session', ''), required, errors, warnings)
    except (OSError, ValueError):
        errors.append('INFLECTION SCAN STATUS MISSING')
    return {'observed_at': utc_now(), 'required_session': required, 'status': 'FAILED' if errors else 'PASS',
            'errors': errors, 'warnings': warnings}


def main():
    result = evaluate()
    from dhruva.deployment import check
    result['errors'] += check()
    result['status'] = 'FAILED' if result['errors'] else 'PASS'
    atomic_write(ROOT/'runs/watchdog/latest.json', canonical(result)+b'\n')
    print(json.dumps(result, indent=1))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
