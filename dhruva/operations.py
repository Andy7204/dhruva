"""Operational wrapper and durable failure evidence for the existing daily job."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import traceback
import uuid

from dhruva.calendar import run_due
from dhruva.ledger import atomic_write, canonical, utc_now, writer_lock

ROOT = Path(__file__).resolve().parents[1]


def write_attempt(record, root=ROOT):
    path = root/'runs/operations'/f"{record['run_id']}.json"
    atomic_write(path, canonical(record)+b'\n')
    atomic_write(root/'runs/operations/latest.json', canonical(record)+b'\n')


def run(refresh=True):
    # Serialize the complete state transition, not just individual ledger writes.
    with writer_lock(ROOT/'runs/pipeline'):
        return _run(refresh)


def _run(refresh=True):
    record = {'run_id': os.getenv('GITHUB_RUN_ID') or str(uuid.uuid4()), 'started_at': utc_now(),
              'event': os.getenv('GITHUB_EVENT_NAME', 'local'), 'strategy_version': '1.0',
              'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'status': 'RUNNING', 'ended_at': None, 'errors': [], 'warnings': [
                  'Accounting defects remain; this is not production-readiness certification.'],
              'stages': {name: {'status':'NOT_RUN'} for name in (
                  'archive','data_ingestion','data_validation','features','benchmark',
                  'portfolio_engine','risk_engine','ledger','report','alerts')},
              'execution_completed': False, 'latest_market_date': None}
    def progress(name, status, detail=None):
        record['stages'][name] = {'status':status, 'observed_at':utc_now(), 'detail':detail}
        write_attempt(record)
    write_attempt(record)
    try:
        due, reason = run_due()
        if not due:
            record.update(status='SKIPPED_NOT_DUE', reason=reason)
        else:
            from qlab.orchestrator import daily_run
            result = daily_run(refresh=refresh, progress=progress)
            date=max(r['state']['as_of'] for r in result['results'])
            record.update(status='DEGRADED', execution_completed=True,
                          market_date=date, latest_market_date=date,
                          data_status=result['data_quality']['status'],
                          decision_status=result['decision_status'],
                          new_evaluations=result['new_evaluations'])
            record['warnings'].extend(result['data_quality'].get('warnings', []))
        return record
    except Exception as exc:
        for stage in record['stages'].values():
            if stage['status']=='RUNNING': stage.update(status='FAILED', error=f'{type(exc).__name__}: {exc}')
        record.update(status='FAILED', errors=[f'{type(exc).__name__}: {exc}'], traceback=traceback.format_exc())
        raise
    finally:
        record['ended_at'] = utc_now()
        write_attempt(record)
        print(json.dumps({k: record[k] for k in ('run_id', 'status', 'ended_at', 'errors')}, indent=2))


def job_outcome():
    """Runs in an always() workflow step even if Python install/tests failed."""
    record = {'run_id': 'job-'+os.environ.get('GITHUB_RUN_ID', str(uuid.uuid4())),
              'generated_at': utc_now(), 'git_commit': os.getenv('GITHUB_SHA'),
              'pipeline_outcome': os.getenv('PIPELINE_OUTCOME', 'unknown'),
              'dependency_outcome': os.getenv('DEPENDENCY_OUTCOME', 'unknown'),
              'test_outcome': os.getenv('TEST_OUTCOME', 'unknown'),
              'note': 'Job evidence; publication status is recorded by GitHub itself.'}
    atomic_write(ROOT/'runs/operations/job_latest.json', canonical(record)+b'\n')
    atomic_write(ROOT/'runs/operations'/f"{record['run_id']}.json", canonical(record)+b'\n')


if __name__ == '__main__': job_outcome()
