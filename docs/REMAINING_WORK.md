# Short release checklist

September25 user priority: finish quickly using minimal credits. The ten-phase
mission remains authoritative; this checklist removes repeated planning, not scope.

1. **Restore green CI and verify deployment (Phase3).** Fix the stale UI-test
   label, confirm corrected99895.67 NAV/ledger on the public app, and inspect the
   next real after-close run. Do not rerun already verified old workflows.
2. **Close economic blockers (Phase3).** Distribution/dividend income and tax,
   adjusted-price versus actual-unit handling, risk stress and shared-account
   execution invariants. Keep specific warnings until supported by evidence.
3. **One reproducible research pass (Phases4–5).** Fix backtest timing/metrics,
   rerun the existing strategy-challenge protocol on pinned inputs, and separate
   reconstructed history from genuine forward returns. No parameter hunting.
4. **Minimum useful completion (Phases6–9).** Reuse current strategy/data/ledger
   components; fix remaining stale CLIs, packaging, research/narrator provenance
   and dashboard claims. Complete strategy card, changelog and architecture/
   compliance documents. Explicitly defer optional ML, agents, API servers,
   commercial features and additional strategies unless evidence requires them.
5. **One final readiness pass (Phase10).** Verify remote daily/watchdog/alerts,
   restart, duplicate, failure recovery, stale UI and preserved evidence. Publish
   the readiness matrix and honest technical case study; list any real blockers.

Use focused tests while editing; one full suite for an integrated change. Reuse
remote evidence and source reviews; inspect deltas rather than rereading the whole
repository. No new dependencies/infrastructure for cosmetic completeness. Advance
phase statuses only on implemented, tested, demonstrated evidence. Stop at5%
remaining in either usage window and update the same continuation heartbeat.
