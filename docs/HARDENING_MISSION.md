# Dhruva: ten-phase execution plan

User amendment, September24, 2026: consolidate the original phases0–25 into
exactly ten phases and execute. This plan supersedes the old numbering, not its
requirements. [Original detailed scope](HARDENING_MISSION_ORIGINAL.md) remains an
acceptance checklist and historical record. Old evidence keeps its original names.

Repair the existing app and initial paper books in place under REPAIR_POLICY.md.
Keep original archive, Git history and immutable events. Label reconstruction and
corrections with actual generation times. Paper only; deterministic trading;
LLMs explain only; no look-ahead; honest costs, taxes and limitations.

| Phase | Work and acceptance | Original scope | Status |
|---|---|---|---|
| 1. Audit and preserve evidence | Capability audit, original manifest/archive, immutable snapshots and decisions; verify persistence, mutation detection and duplicate safety. | 0–2 | Complete, recorded evidence |
| 2. Restore reliable live operation | Calendar-safe canonical daily run, causal validated data, one dashboard NAV, stage health, independent watchdog, external alerts, safe publication and demonstrated failure/recovery. Verify actual after-close output and public app. | 3–10 | In progress; original0–8 complete,9–10 pending |
| 3. Repair paper accounting and execution | Shared FIFO tax reserve, correct NAV/cash, settlement cash restrictions and calendar, accurate instrument costs/tax, permanent orders and IDs, next-open/gap-stop fills, risk invariants; reconcile initial history transparently. | Audited fixes plus execution/accounting parts of13/22 | Pending |
| 4. Validate historical research | Correct execution and metrics; costs/tax, no leakage, walk-forward/regime/sensitivity tests. Reproduce challenge study and test 200-day lag,63-day delay, common filter, dip-buying and opportunity costs under equal assumptions. No return-driven tuning or automatic strategy promotion. | 11 and strategy-challenge request | Pending |
| 5. Separate and verify performance | Distinct historical, reconstructed and genuine timestamped forward results; live index100, preselected benchmarks, reconciled after-cost/tax metrics and full limitations. | 12 | Pending |
| 6. Simplify portfolio and strategy architecture | Enforce sizing, sectors, liquidity, turnover, cash and exit constraints; shared strategy interface; current strategy first; useful paper execution boundary only. No real broker orders or invented product families. | Remaining13,14–15,22 | Pending |
| 7. Make research and narration traceable | Indian-source research with publication/retrieval timestamps and URLs; provenance and failure states; narration cannot change trades. Audit ML and agent claims, implement only measurable useful capability or explicitly defer with evidence. | 16–18 | Pending |
| 8. Finish the trustworthy public dashboard | Home, decisions, portfolio, separated performance, sourced research, methodology and health; strategy card, changelog and history labels; verify deployed behavior. | 19–20 | Pending |
| 9. Document architecture and release boundaries | Decide API usefulness; future-product architecture and compliance gates with sourced, limited claims. No commercial features or live trading. | 21,23–24 | Pending |
| 10. Prove readiness and publish the case study | End-to-end remote/restart/recovery/alert/duplicate/stale acceptance evidence in PRODUCTION_READINESS.md; honest AI-assisted TECHNICAL_CASE_STUDY.md. Close audited findings or explicitly identify unresolved release blockers. | 25 and final readiness | Pending |

## Execution and completion rules

Complete each phase sequentially: inspect, implement, test, demonstrate, document,
commit, then continue. Preserve detailed acceptance requirements from the original
scope. Grouping phases does not turn partial work into completion. Phase2 may
retain explicit accounting warnings until Phase3; never imply economic health
from a successful workflow. Final readiness cannot pass with material open errors.

Report changed files, tests, actual evidence, issues and justified deferrals at each
phase boundary. Conditional API/ML/agent/commercial work may be rejected with a
reason; required accounting, reliability and strategy tests may not be waived.

Check usage at start and phase boundaries. At10% or less remaining in either core
window, checkpoint and resume after the limiting reset through the existing
continuation heartbeat. Never buy credits or redeem reset credits. Minimize repeated
reads, redundant full tests and unnecessary infrastructure. Keep working beyond
this plan document until the requested outcomes are verified.
