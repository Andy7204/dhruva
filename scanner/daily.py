"""Daily inflection pipeline after the index books: Stages 1-2, audit, Stage 3 queue, report, notice.

Failures here never touch the index paper books.
"""
import json
import sys
from datetime import datetime

from dhruva.calendar import IST, expected_date, run_due


def main():
    now = datetime.now(IST)
    if not run_due(now)[0] and '--force' not in sys.argv:
        print('Not due'); return 0
    session = expected_date(now)
    from scanner.run import run as stages12
    from scanner import audit, notify
    from scanner.data import universe
    from underwriter.run import run as stage3
    status, stage1, _ = stages12(session)
    print(json.dumps(status, indent=1))
    try:
        audit.seed_cases()
        from scanner.data import CACHE
        import pandas as pd
        frames = {}
        for sym in stage1['symbol']:
            p = CACHE/'prices'/((sym+'.NS').replace('^', '_').replace('&', '_')+'.csv')
            if p.exists(): frames[sym] = pd.read_csv(p, index_col=0, parse_dates=True)
        new = audit.run(frames, set(universe()['symbol']), session)
        print(f'audit: {len(new)} new missed-winner cases')
    except Exception as exc:
        print(f'audit failed: {type(exc).__name__}: {exc}')
    print(json.dumps(stage3(session), indent=1, default=str))
    print(json.dumps(notify.build(session), indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
