"""Daily paper update: guard, fetch completed-session data, replay books, record.

    python -m dhruva.daily            # normal guarded run
    python -m dhruva.daily --force    # ignore the time guard (never the data checks)
"""
import argparse
import json
import traceback
from datetime import datetime
from pathlib import Path

from dhruva.calendar import IST, expected_date, run_due
from dhruva.util import atomic_write, canonical, utc_now

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['NIFTY_50', 'NIFTY200_MOMENTUM_30', 'NIFTY_MIDCAP150_MOMENTUM_50', 'GOLDBEES']


def run(root=ROOT, now=None, force=False):
    from dhruva import marketdata, forward, digest
    now = now or datetime.now(IST)
    status = {'started_at': utc_now(), 'status': 'RUNNING', 'errors': [], 'warnings': []}
    try:
        due, reason = run_due(now)
        if not due and not force:
            status.update(status='SKIPPED_NOT_DUE', reason=reason)
            return status
        session = expected_date(now)
        status['session'] = session
        status['data'] = marketdata.update(session)
        stale = [f for f in REQUIRED if marketdata.latest(f) < session]
        if stale:
            raise RuntimeError('Data not yet published for '+session+': '+', '.join(stale))
        cfg = forward.config(root)
        books = forward.replay(cfg, through=session)
        if not books:
            status.update(status='NOT_STARTED', reason='Forward start '+cfg['forward_start']+' not reached')
            return status
        previous = json.loads((root/'runs/forward/state.json').read_text(encoding='utf-8')) if (root/'runs/forward/state.json').exists() else {}
        status['warnings'] += forward.record(books, root)
        note = digest.build(previous, books)
        (root/'runs/digest.json').write_text(json.dumps(note, indent=1, ensure_ascii=False), encoding='utf-8')
        status.update(status='SUCCESS', as_of=session)
        return status
    except Exception as exc:
        status.update(status='FAILED', errors=[f'{type(exc).__name__}: {exc}'], trace=traceback.format_exc()[-2000:])
        return status
    finally:
        status['ended_at'] = utc_now()
        atomic_write(root/'runs/status.json', canonical(status)+b'\n')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--force', action='store_true')
    result = run(force=p.parse_args().force)
    print(json.dumps({k: v for k, v in result.items() if k != 'trace'}, indent=1))
    raise SystemExit(1 if result['status'] == 'FAILED' else 0)


if __name__ == '__main__':
    main()
