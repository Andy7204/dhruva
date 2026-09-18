"""Synthetic permanent acceptance fixture, separate from all live/research tracks."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dhruva.ledger import Ledger


def main():
    ledger = Ledger(ROOT/'runs/ledger/acceptance_test_only')
    key = 'phase2-synthetic-signal-v1'
    existing = ledger.find(key)
    if existing:
        events = [{k: v for k, v in e.items() if k != 'event_id'} for e in existing['payload']['events']]
        _, added = ledger.append(key, events)
    else:
        from dhruva.ledger import utc_now
        now = utc_now()
        snapshot = ledger.snapshot({'fixture': True, 'price': 100., 'signal': 'BUY', 'not_market_data': True})
        event = dict(run_id=key, generated_at=now, data_cutoff_at=now, effective_date=now[:10],
                     strategy_id='TEST_ONLY_NOT_LIVE', strategy_version='test', git_commit='synthetic-fixture',
                     configuration_hash='synthetic-fixture', data_snapshot=snapshot, ticker='TEST_ONLY',
                     company_name='Synthetic fixture, no security', action='BUY', previous_weight=0,
                     target_weight=.1, signal_score=1., signal_components={'synthetic': True},
                     market_price=100., rationale='Ledger durability acceptance fixture; no real or live signal',
                     portfolio_nav=1000., benchmark_level=None, execution_mode='PAPER', execution_status='TEST_ONLY')
        _, added = ledger.append(key, [event])
    print(json.dumps(dict(ledger.verify(), new_event_written=added), indent=2))


if __name__ == '__main__': main()
