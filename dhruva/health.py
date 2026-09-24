"""Read-only health: a dated file or successful job is not proof of correctness."""
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import subprocess
from dhruva.calendar import IST, expected_date
from dhruva.freeze import verify_v1
from dhruva.ledger import Ledger
ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def inspect(root=ROOT, now=None):
    root = Path(root); now = now or datetime.now(IST)
    result = dict(status='DEGRADED', problems=[], warnings=[
        'Current paper NAV is before tax: tax is not reserved and T+1 cash restrictions are not enforced.',
        'Recorded observations have known audit defects; they are not a validated live track record.'],
        books=[], total=None, starting_capital=None, market_date=None, portfolio_date=None,
        expected_date=None, last_success=None, last_attempt=None, strategy_version='1.0', git_commit='unavailable')
    try:
        result['git_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True,
                                                       stderr=subprocess.DEVNULL, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        result['warnings'].append('Deployment commit unavailable.')
    try: result['expected_date'] = expected_date(now)
    except ValueError as exc: result['problems'].append(str(exc))
    try: verify_v1(root)
    except Exception as exc: result['problems'].append(f'Frozen strategy integrity: {exc}')
    try:
        cfg = read_json(root/'config.json'); books = []
        for name, spec in cfg['books'].items():
            state = read_json(root/'runs'/f'livebook_{name}.json')
            date, value = state['history'][-1]
            if (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or
                    state['capital'] != spec['capital'] or state['as_of'] != date):
                raise ValueError(f'{name}: invalid capital, NAV or date')
            books.append(dict(name=name, value=value, capital=spec['capital'], as_of=date, state=state))
        if not books or len({b['as_of'] for b in books}) != 1:
            raise ValueError('Portfolio books have inconsistent dates')
        result.update(books=books, total=sum(b['value'] for b in books),
                      starting_capital=sum(b['capital'] for b in books), portfolio_date=books[0]['as_of'])
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        result['problems'].append(f'PORTFOLIO UNAVAILABLE: {exc}')
    try:
        with (root/'data/cache/_IDX_NSEI.csv').open(encoding='utf-8') as stream:
            dates = [row['date'][:10] for row in csv.DictReader(stream)]
        result['market_date'] = max(dates)
    except (OSError, ValueError, KeyError) as exc:
        result['problems'].append(f'MARKET DATA UNAVAILABLE: {exc}')
    if result['expected_date']:
        for field, label in [('market_date', 'MARKET DATA'), ('portfolio_date', 'PORTFOLIO')]:
            date = result[field]; expected = result['expected_date']
            if date and date < expected: result['problems'].append(f'{label} STALE: {date}; expected {expected}')
            if date and date > expected: result['problems'].append(f'{label} has an unfinished or future session: {date}')
    op = root/'runs/operations'
    try:
        if (op/'latest.json').exists():
            result['last_attempt'] = read_json(op/'latest.json')
            status = result['last_attempt'].get('status')
            if status in ('FAILED', 'RUNNING'):
                result['problems'].append('BACKEND '+status+': '+str(result['last_attempt'].get('errors', [])))
        else: result['problems'].append('PIPELINE HISTORY UNAVAILABLE: no operational heartbeat')
        completed = []
        for path in op.glob('*.json'):
            record = read_json(path)
            if record.get('status') in ('COMPLETED_UNVERIFIED_DATA', 'SUCCESS', 'SUCCESS_NO_ACTION') or (
                    record.get('status')=='DEGRADED' and record.get('execution_completed')):
                completed.append(record)
        if completed: result['last_success'] = max(completed, key=lambda r: r.get('ended_at') or '')
        if (op/'job_latest.json').exists():
            job = read_json(op/'job_latest.json')
            if any(job.get(k) in ('failure', 'cancelled') for k in ('pipeline_outcome', 'dependency_outcome', 'test_outcome')):
                result['problems'].append('LATEST GITHUB JOB FAILED: '+str(job['run_id']))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['problems'].append(f'OPERATIONAL EVIDENCE UNREADABLE: {exc}')
    ledger = root/'runs/ledger/dhruva_v1'
    quality_path = root/'runs/data_quality.json'
    if quality_path.exists():
        try:
            result['data_quality'] = read_json(quality_path)
            if result['data_quality']['status'] == 'FAILED':
                result['problems'].append('DATA VALIDATION FAILED: '+str(result['data_quality'].get('errors', [])))
            if result['data_quality'].get('excluded'):
                result['warnings'].append('Data exclusions: '+', '.join(result['data_quality']['excluded']))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result['problems'].append(f'DATA VALIDATION UNREADABLE: {exc}')
    if (ledger/'segments').exists():
        try: result['ledger'] = Ledger(ledger).verify()
        except Exception as exc: result['problems'].append(f'LEDGER INTEGRITY FAILED: {exc}')
    else: result['warnings'].append('Prospective ledger awaits its first completed-session evaluation.')
    if result['problems']: result['status'] = 'UNHEALTHY'
    # Never GREEN for v1: known accounting defects and incomplete data validation.
    return result
