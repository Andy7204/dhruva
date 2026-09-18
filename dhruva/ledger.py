"""Small Git-backed, append-only, hash-chained paper evidence store.

Single writer lock, atomic segment publication, idempotency conflict detection,
and a separate checkpoint detect edits, holes and truncation. No update/delete API.
Git is the durable external copy; an administrator can still rewrite the repository.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

ZERO = '0' * 64
REQUIRED = {'run_id', 'generated_at', 'data_cutoff_at', 'effective_date', 'strategy_id',
            'strategy_version', 'git_commit', 'configuration_hash', 'data_snapshot',
            'ticker', 'company_name', 'action', 'previous_weight', 'target_weight',
            'signal_score', 'signal_components', 'market_price', 'rationale',
            'portfolio_nav', 'benchmark_level', 'execution_mode', 'execution_status'}
ACTIONS = {'BUY', 'SELL', 'HOLD', 'INCREASE', 'REDUCE', 'NO_ACTION', 'CORRECTION'}


class LedgerError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def writer_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / '.writer.lock'
    with path.open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def atomic_write(path, data):
    """Atomic same-directory replacement; caller owns lock and overwrite policy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_event(event):
    missing = REQUIRED - event.keys()
    if missing:
        raise LedgerError('Missing event fields: '+', '.join(sorted(missing)))
    if event['action'] not in ACTIONS or event['execution_mode'] not in {'PAPER', 'SHADOW'}:
        raise LedgerError('Unsupported action or non-paper execution mode')
    for field in ('generated_at', 'data_cutoff_at'):
        try:
            value = datetime.fromisoformat(event[field])
            if value.tzinfo is None:
                raise ValueError('timezone required')
        except (ValueError, TypeError) as exc:
            raise LedgerError(f'{field} requires an explicit timezone') from exc
    if datetime.fromisoformat(event['data_cutoff_at']) > datetime.fromisoformat(event['generated_at']):
        raise LedgerError('Data cutoff is after generation time')
    for field in ('previous_weight', 'target_weight', 'signal_score', 'market_price',
                  'portfolio_nav', 'benchmark_level'):
        value = event[field]
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise LedgerError(f'{field} must be finite or explicitly null')
    if event['action'] == 'CORRECTION' and not event.get('corrects_event_id'):
        raise LedgerError('A correction must reference its original event')
    canonical(event)


class Ledger:
    def __init__(self, root):
        self.root = Path(root)

    def _read(self):
        previous = ZERO
        result = []
        keys = set()
        try:
            for i, path in enumerate(sorted((self.root/'segments').glob('*.json')), 1):
                envelope = json.loads(path.read_bytes())
                payload = envelope['payload']
                expected = digest(payload)
                if (envelope['hash'] != expected or payload['sequence'] != i or
                        payload['previous_hash'] != previous or path.name != f'{i:08d}-{expected}.json'):
                    raise LedgerError(f'Ledger integrity failure: {path.name}')
                for event in payload['events']:
                    validate_event(event)
                events = [{k: v for k, v in e.items() if k != 'event_id'} for e in payload['events']]
                if digest({'events': events, 'state': payload['state']}) != payload['content_hash']:
                    raise LedgerError('Segment content fingerprint mismatch')
                for number, event in enumerate(events):
                    if payload['events'][number]['event_id'] != digest([payload['idempotency_key'], number, event]):
                        raise LedgerError('Event identity mismatch')
                if payload['idempotency_key'] in keys:
                    raise LedgerError('Duplicate evaluation key in ledger')
                keys.add(payload['idempotency_key'])
                previous = expected
                result.append(envelope)
            cp = self.root/'checkpoint.json'
            if cp.exists():
                checkpoint = json.loads(cp.read_bytes())
                n = checkpoint['sequence']
                if n < 1 or n > len(result) or result[n-1]['hash'] != checkpoint['hash']:
                    raise LedgerError('Checkpoint mismatch: ledger changed or truncated')
            elif result:
                # First segment may have published before checkpoint on a crash.
                if len(result) != 1:
                    raise LedgerError('Missing ledger checkpoint')
            return result
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise LedgerError(f'Cannot read ledger: {exc}') from exc

    def verify(self, expected_head=None, verify_snapshots=True):
        with writer_lock(self.root):
            records = self._read()
            head = records[-1]['hash'] if records else ZERO
            if expected_head is not None and head != expected_head:
                raise LedgerError('Published anchor does not match ledger head')
            if verify_snapshots:
                for key in {e['data_snapshot'] for r in records for e in r['payload']['events'] if e['data_snapshot']}:
                    self.read_snapshot(key)
            return {'segments': len(records), 'events': sum(len(x['payload']['events']) for x in records),
                    'head': head}

    def find(self, idempotency_key):
        with writer_lock(self.root):
            return next((x for x in self._read() if x['payload']['idempotency_key'] == idempotency_key), None)

    def append(self, idempotency_key, events, state=None):
        if not events or not idempotency_key:
            raise LedgerError('Nonempty idempotency key and evaluation events required')
        for event in events:
            validate_event(event)
        content = {'events': events, 'state': state}
        fingerprint = digest(content)
        with writer_lock(self.root):
            records = self._read()
            prior = next((r for r in records if r['payload']['idempotency_key'] == idempotency_key), None)
            if prior:
                if prior['payload']['content_hash'] != fingerprint:
                    raise LedgerError('Idempotency conflict; original evidence must not be replaced')
                last = records[-1]
                atomic_write(self.root/'checkpoint.json', canonical(
                    {'sequence': len(records), 'hash': last['hash']})+b'\n')
                return prior, False
            ids = {e['event_id'] for r in records for e in r['payload']['events']}
            stamped = []
            for i, event in enumerate(events):
                if event['action'] == 'CORRECTION' and event['corrects_event_id'] not in ids:
                    raise LedgerError('Correction references an unknown prior event')
                stamped.append(dict(event, event_id=digest([idempotency_key, i, event])))
            sequence = len(records)+1
            payload = {'sequence': sequence, 'previous_hash': records[-1]['hash'] if records else ZERO,
                       'idempotency_key': idempotency_key, 'content_hash': fingerprint,
                       'events': stamped, 'state': state}
            envelope = {'hash': digest(payload), 'payload': payload}
            path = self.root/'segments'/f"{sequence:08d}-{envelope['hash']}.json"
            if path.exists():
                raise LedgerError('Refusing to replace an existing segment')
            atomic_write(path, canonical(envelope)+b'\n')
            # A crash here leaves a valid extra segment; the checkpoint may lag,
            # never lead. Re-entry verifies the complete chain before proceeding.
            atomic_write(self.root/'checkpoint.json', canonical({'sequence': sequence, 'hash': envelope['hash']})+b'\n')
            return envelope, True

    def snapshot(self, value):
        """Content-addressed immutable exact input object; compression has no timestamp."""
        raw = canonical(value)
        key = hashlib.sha256(raw).hexdigest()
        path = self.root/'snapshots'/f'{key}.json.gz'
        with writer_lock(self.root):
            if path.exists():
                if gzip.decompress(path.read_bytes()) != raw:
                    raise LedgerError('Snapshot content changed')
            else:
                atomic_write(path, gzip.compress(raw, mtime=0))
        return key

    def read_snapshot(self, key):
        if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise LedgerError('Invalid snapshot identifier')
        try:
            raw = gzip.decompress((self.root/'snapshots'/f'{key}.json.gz').read_bytes())
            if hashlib.sha256(raw).hexdigest() != key:
                raise LedgerError('Snapshot integrity failure')
            return json.loads(raw)
        except (OSError, ValueError, EOFError) as exc:
            raise LedgerError(f'Cannot read snapshot: {exc}') from exc
