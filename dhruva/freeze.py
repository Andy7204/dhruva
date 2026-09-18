"""Fail closed when a frozen strategy or its evidence changes.

Hashes detect accidental/local changes; a repository administrator can rewrite
both hashes and history. Git publication is an external checkpoint, not WORM storage.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FrozenStrategyChanged(RuntimeError):
    pass


def verify_v1(root=ROOT, *, check_active=True):
    root = Path(root)
    frozen = root / 'strategies/dhruva_v1'
    manifest_path = frozen / 'strategy_manifest.yaml'
    try:
        raw = manifest_path.read_bytes()
        expected = (frozen / 'manifest.sha256').read_text().strip()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise FrozenStrategyChanged('Frozen v1 manifest changed.')
        manifest = json.loads(raw)
        mismatches = []
        for path, digest in manifest['snapshot_files'].items():
            actual = (frozen / 'snapshot' / path).read_bytes()
            if hashlib.sha256(actual).hexdigest() != digest:
                mismatches.append('snapshot/'+path)
        if check_active:
            for path in manifest['active_guard_files']:
                # Git autocrlf may change a text checkout; it does not change semantics.
                actual = (root / path).read_bytes().replace(b'\r\n', b'\n')
                if hashlib.sha256(actual).hexdigest() != manifest['snapshot_files'][path]:
                    mismatches.append(path)
        if mismatches:
            raise FrozenStrategyChanged('Frozen v1 changed: '+', '.join(mismatches)+
                                        '. Create a new prospective version; do not overwrite v1.')
        return manifest
    except (OSError, KeyError, ValueError) as exc:
        raise FrozenStrategyChanged(f'Cannot verify frozen v1: {exc}') from exc


if __name__ == '__main__':
    m = verify_v1()
    print(f"Verified Dhruva {m['strategy_version']}: {len(m['snapshot_files'])} frozen files.")
