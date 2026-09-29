"""Independent read-only liveness check; never fetches prices or changes books."""
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path

from dhruva.calendar import IST, expected_date
from dhruva.util import atomic_write, canonical, utc_now

ROOT = Path(__file__).resolve().parents[1]


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
        if left <= 14:
            errors.append(f'CALENDAR MAINTENANCE: trading calendar ends {cal["valid_through"]}, {left} days left. Add official NSE dates.')
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
        if required and as_of < required:
            errors.append(f'BOOKS STALE: recorded {as_of}, required {required}')
    except (OSError, ValueError, KeyError):
        cfg = json.loads((Path(root)/'config.v2.json').read_text(encoding='utf-8'))
        if required and required > cfg['forward_start']:
            errors.append('FORWARD BOOKS MISSING')
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
