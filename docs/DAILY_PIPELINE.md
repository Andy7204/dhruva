# Canonical daily pipeline

Run `python -m dhruva.run_daily` (or `--no-refresh` for cache inputs). The legacy
`scripts/daily_run.py` delegates to this same guarded CLI. Actions calls the module.
Before16:30 IST, weekends and known holidays skip without advancing paper books.

One process lock covers the operation. Verify original archive, acquire data,
build features and benchmark-aligned sessions, recover committed ledger state,
advance every unprocessed session, append each date's complete two-book bundle,
publish projections, generate prose/report and operational result. Recovery dates
are explicitly RECOVERY_RECONSTRUCTION with actual generation timestamps.
They are not retrospectively claimed as original live decisions.

An interruption after ledger append but during projection publication is repaired
from that exact committed bundle. Same-date reruns retain the first captured
results rather than revised quotes. Inconsistent checkpoints without ledger
evidence fail; missing regime observations fail rather than defaulting risk-on.
No-action output says `NO ACTION — strategy unchanged`; all intents are paper-only.

September24 evidence:28 tests passed, including a complete mocked-data pipeline
interrupted between book writes, recovery of three sessions, and duplicate rerun.
Actual CLI run58b72a8f-29ba-40ba-af0a-b6a7a00d0d83 returned SKIPPED_NOT_DUE
at09:28 UTC, before market finalization. No clock override or intraday advance.

The original archive remains hash-verified. Active-source equality is optional
(`verify_v1(check_active=True)`) for original-baseline diagnostics only. The user
authorized active in-place repairs. Archive files and old events were not rewritten.

Limitations: strict data validation is Phase6; full per-stage health Phase7;
independent watchdog/external alerts Phases8–9. Economics remain under repair.
This phase does not certify tax/settlement or final production readiness.
