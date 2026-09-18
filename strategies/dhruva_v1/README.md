# Dhruva v1.0 — frozen original experiment

`strategy_manifest.yaml` is JSON-compatible YAML, including exact definitions,
assumptions, source revision and SHA-256 file inventory. `snapshot/` contains
unaltered Git blob bytes from `75dd97e0cca9a89f7f2c1dec6706607cab388e40`.
The original cache is preserved by that Git revision. This archive includes
known defects; it is not endorsed as a correct accounting engine.

Recorded inception is September 16, 2026. Original events lack individual UTC
generation timestamps and data snapshots. Do not fabricate that provenance or
classify imported historical simulations as genuine forward records.

Run `python -m dhruva.freeze` to verify the archive and active v1 economic code.
The daily orchestrator verifies before it fetches data or changes state. Changes
to ranking, inputs, execution, settlement, tax or NAV need a new version and
separate state/ledger, with a prospective start. Formatting-only infrastructure
outside guarded economic files may retain v1 after decision-equivalence testing.

Never regenerate this manifest/archive to silence a mismatch. Tests deliberately
mutate temporary copies. The original archive is immutable by application policy,
hash-checked and Git-published; this is not administrator-proof WORM storage.
