# Short release checklist

September25 user priority: finish quickly using minimal credits. The ten-phase
mission remains authoritative; this checklist removes repeated planning, not scope.

1. **Verify new code only (Phase3).** Earlier CI, corrected public NAV and Sep25
   after-close daily are verified; do not repeat those tasks. Check latest791d751
   CI, then obtain a genuine trading-session acceptance of the new quoted-unit,
   receipt and per-lot settlement code when the market next closes.
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
