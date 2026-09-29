"""Daily inflection funnel after the paper books: Stages 1-2, then Stage 3 if a key exists.

Failures here never touch the index paper books; they are recorded in
runs/inflection/status.json and fail this step so the incident alert fires.
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
    from underwriter.run import run as stage3
    status, _, _ = stages12(session)
    print(json.dumps(status, indent=1))
    result = stage3(session)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
