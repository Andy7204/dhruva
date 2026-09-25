# Dhruva hardening checkpoint

Mission: [HARDENING_MISSION.md](HARDENING_MISSION.md). Follow the ten consolidated phases in order.
Read AGENTS.md fully before resuming. Paper research only; deterministic decisions;
preserve existing history and distinguish imported records from prospective evidence.

## Current checkpoint

LATEST September25 Phase3: core repair code ba705dd,59 tests passed. Initial
correction applied at actual September25 generation time, producing ba705dd;
ledger head7fd1a82305f5c7957fe4911e9858a0596039a1a7f9ebc9b30a0eaea0c33caabb.
Same82GOLDBEES+3LIQUIDBEES; latest modeled-reserve NAV99895.67,13.19 above old
99882.48 from corrected ETF fees. September17 close separately reconstructed.
Original five segments untouched; correction is sixth segment with two events.
Core FIFO/shared exemption/settled cash/orders/gap fills fixed; distribution income,
adjusted-price limits, further risk stress and real after-close acceptance pending.


LATEST September25: new Phase2 complete within its operational scope; Phase3
accounting/execution repairs starting. Real daily retry36017079889 succeeded;
scheduled36035932204 succeeded with zero additional evaluations. Watchdog36074243248
and CI36017696913 passed. Public3e57688 shows Sep24 and single99882.48 before-tax NAV,
no stale warning, explicit accounting limitations. Five immutable segments/5016 events
verified, no projection mismatch. Evidence: phase2_live_recovery_2026-09-25.json and
PHASE2_ACCEPTANCE.md. Start usage0% five-hour31% weekly. Threshold5% remaining.


Latest user amendment: stop at **5% remaining**, replacing10%. Fresh usage95%
five-hour/30% weekly, so the new cutoff is already reached. Reset/resume times
remain September25 01:18:24/01:25 IST.


LATEST September24 evening: user approved ten-phase consolidation, committed
f834426. New Phase1 complete; new Phase2 in progress.45 local tests pass.
f34e184 adds daily external failure alerts and ledger/projection equality checks;
f7ae72e adds actual Streamlit runtime probe and cash/quantity risk validation.
Remote CI36017054570 passed; CI for f7ae72e still needs checking. Normal watchdog
36016354838 and synthetic external alert36016083742 passed; test issue3 closed.
Daily retry36017079889 (job107692268363) still fetching/calculating at checkpoint.
FIRST next turn inspect its result/logs, fetch committed outputs, verify ledger and
public dashboard; do not dispatch another run unnecessarily. Safe publisher may
rebase over these source/docs commits. Prior daily36015761872 publication failed
(fetch first); its old artifact lacks ledger/cache, never backdate reconstructed data.
Public browser verified f834426 loading with Sep23 stale warnings and one99,989.11
pre-tax total. Actual iframe `/~/+/_stcore/health` returned200ok. Root endpoint was
HTML/303 and must not be treated as health. Watchdog new probe needs remote run.
Current usage90% five-hour,29% weekly: stop per user guard. Limiting reset
2026-09-25T01:18:24+05:30. Resume same heartbeat01:25 IST. No reset redeemed.
Finish Phase2 external failure/recovery demonstration and refreshed public output;
then Phase3 in-place accounting/execution repairs. Full risk limits still pending.



September24 user amendment: exactly ten phases now govern execution; see
HARDENING_MISSION.md for complete mapping. **New Phase1 complete; new Phase2 in
progress.** Historical phase numbers below refer to the archived original plan.
Original phases0–8 have evidence; original9–10 and actual refreshed publication
remain the immediate gate. New Phase3 contains all in-place accounting/execution
repairs. No remaining scope was dropped or automatically marked complete.


- USER AMENDMENT September18: fix the existing version and paper books in place;
  do not create a separate degraded product or parallel strategy version. Follow
  `docs/REPAIR_POLICY.md` over the older new-track wording in historical phase logs
  and the original mission. Keep the existing archive/Git history as evidence.
- Change the active-source hash guard to archive-only when implementing fixes.
  Do not hide current defects by just changing the status label. Recalculated
  initial paper history must be labelled honestly; simulated Sep17 fills do exist.

- Phases 0–4 complete. Phase4 after-close evidence verified September24; see
  `docs/evidence/phase4_after_close.json` and updated public observation.
- Phase5 complete September24: canonical CLI, chronological recovery, whole-run
  lock, ledger-based projection recovery and archive-only guard.28 tests pass.
- Phase6 complete September24: DATA_CONTRACT.md;34 tests pass, actual cache
  validation99.206% coverage with four explicit exclusions. Causal cleaner and
  adjusted indicators repaired. Production after-close run of new rules still due.
- Phase7 complete: durable stage transitions, exact errors and explicit skipped,
  failed or executed-with-known-limitations outcomes.35 tests pass; RUN_HEALTH.md.
- Phase8 complete: remote normal watchdog36016354838 and external alert test
 36016083742 passed. See evidence/phase8_remote_acceptance.md. Phase9 in progress:
 daily failure alerts and portfolio/ledger mismatch checks added; broader deployment
 and risk coverage still pending. Accounting repairs remain pending.
- Latest verified CI35305870599 succeeded; manual daily35305448785 correctly
  skipped the unfinished session. No accounting fixes are claimed complete yet.
- Frozen original v1 source/data baseline remains `75dd97e`; never rewrite it.
- Public repository: https://github.com/Andy7204/dhruva
- Public app: https://dhruva-andy7204.streamlit.app/
- GitHub scheduled run `35252434924` succeeded September 17, 2026,
  17:23:24–17:28:32 UTC. Scheduled cron was 13:00 UTC; actual dispatch was late.
- Do not correct execution/accounting before freezing v1 in Phase 1.
- Do not mark a phase complete until implemented, tested, demonstrated and committed.
- No later phases are complete yet.

## Continuation and usage

- User authorized continuation until all tasks are complete, including after resets.
- Thread heartbeat ID: `continue-dhruva-hardening-after-usage-reset`, currently
  daily14:40,16:40,19:40 local time for reset and completed-session checks.
- Local continuation requires this computer and Codex to remain running. GitHub daily
  execution is independent of the local computer.
- Check fresh usage at phase boundaries. At <=5% remaining in either core window,
  checkpoint exact next action and limiting reset, then defer until capacity returns.
- Reset confirmed September18 at09:12 UTC: five-hour usage21% (79% left), next
  reset Unix1789740760; weekly usage84% (16% left), reset September24 10:44:15 IST
  (Unix1790226855). Current wait is the completed-session acceptance gate,
  not five-hour exhaustion. Keep checking BOTH windows. No purchases/resets.
- Do not buy credits or redeem a reset. Do not create another continuation task.
- Python: `C:/Users/adpan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
- Shell PowerShell. Git push works; gh CLI is absent. GitHub connector reads run
  evidence; browser can dispatch. Avoid printing credentials or secret values.

## Phase register

| Phase | Status | Evidence / next action |
|---|---|---|
| 0 | Complete | CURRENT_STATE_AUDIT.md, 11 engineering observations, nine quant defect reproductions; production hashes unchanged. |
| 1 | Complete | 52-file v1 archive, manifest, 13 active guarded paths; five tests and CLI verification passed. |
| 2 | Complete | Immutable segments/snapshots and v1 capture; 13 tests; fresh remote checkout/restarted process preserved head and did not duplicate fixture. |
| 3 | Complete | 16 tests and clean Linux install passed remotely; manual35305448785 correctly skipped unfinished session and published durable evidence. |
| 4 | Complete | Four real scheduled refreshes; public Sep23 data at ece92f3;4,016 ledger events/hash-checked snapshots; copied-real-bundle duplicate capture safe. |
| 5 | Complete | DAILY_PIPELINE.md;28 tests, interrupted two-book publication/recovery/duplicate fixture; actual guarded CLI skip. |
| 6 | Complete | DATA_CONTRACT.md,34 tests and phase6_data_quality.json real-cache evidence. Economics audited, still explicitly pending repairs. |
| 7 | Complete | RUN_HEALTH.md;35 tests, stale-benchmark failure retains failed stage and portfolio NOT_RUN. New-schema after-close observation pending. |
| 8 | In progress | WATCHDOG.md;38 tests; local real-evidence operational PASS; remote and notification acceptance pending. |
| 9–10 | Not started | Alerting, failure recovery and live economic repairs. |
| 11–15 | Not started | Backtest, live separation, portfolio, interface, actual strategies. |
| 16–20 | Not started | Sourced research, explanation layer, ML decision, UX, strategy cards. |
| 21–25 | Not started | API/execution decisions, architecture/compliance docs, honest case study. |

## Phase report log

Phase 0 completed September 18: full matrix, current architecture, dangerous and
missing components, ordered remediation plan. Both reproducible audit scripts
passed; eight research tests passed; 2,380 / 2,415 protected files unchanged.
Decisions: freeze original behavior before fixes; no ML, agent swarm or API server.
Next: Phase 1 version manifest, frozen snapshots, mutation guard and tests.

Phase 1 completed September 18: exact 52-file archive at deployed `75dd97e`,
manifest covering required strategy assumptions and known defects, 13 guarded
economic paths, and fail-closed daily entrypoint. Five tests passed, including
source/config/universe/history/manifest tamper and rejection before fetching.
Evidence: `docs/evidence/phase1_freeze.json`. No economic fixes applied yet.
Next: Phase 2 durable append-only ledger; separate synthetic acceptance namespace
from imported legacy history and genuinely prospective decisions.

Phase 2 completed September 18: `dhruva/ledger.py`, `dhruva/evidence.py`, daily
orchestrator capture, ledger/evidence tests, `scripts/ledger_acceptance.py`,
`docs/LEDGER.md`, `.gitattributes`, `.gitignore`, and synthetic ledger namespace.
Implementation pushed at `00b813a`. Thirteen tests passed. A fresh sparse clone
from public GitHub and a new Python process returned the identical ledger head
`dd5c4a3a614f41ae313bf026af853f4a3514199f74ac53800b6d76981ef6cc61`,
one event, and `new_event_written=false`; evidence `phase2_remote_restart.json`.
Corrections append; mutations/truncation fail. Snapshot corruption fails.
This is tamper-evident Git storage, not administrator-proof immutability.
No economic bugs claimed repaired. Next: Phase 3 workflow/dependency hardening,
then Phase 4 deployed freshness and failure visibility. Do not start Phase 5
until combined acceptance evidence is complete.

Phase3 completed: workflow and dependency pins, safe time/calendar guard,
always-run outcome publication, tests workflow. Remote CI35305417648 and manual
daily35305448785 succeeded. Generated commit `e45caaf` retrieved. No optional
repository/environment secrets exist; basic operation needs none. No Telegram
or LLM delivery claimed. Manual morning run intentionally did not refresh data.
Next Phase4: one authoritative displayed value, visible stale/corrupt/failure
states, version/commit/time information, local UI tests and real deployment check.
Combined gate also needs actual hardened after-close refresh; do not bypass it.

Phase4 in progress: `dhruva/health.py`, `streamlit_app.py`, health/UI tests and
`docs/STREAMLIT_VERIFICATION.md`. 23 tests pass locally. One saved valuation,
before-tax label, no misleading legacy HTML, explicit stale/corrupt/failed states
and per-minute health refresh. Next: verify deployed page/commit, then real
after-close refresh (earliest16:30 IST; normal schedule18:30 IST). Do not fabricate
a completed-session run in the morning or advance to Phase5 before this gate.

Phase4 deployment observed September18 around04:10 UTC: public browser showed
commit75c5c75, SYSTEM DEGRADED, one NAV INR99,914.49, correct book totals,
Sep17 portfolio/benchmark dates and the morning SKIPPED_NOT_DUE attempt.
Remote CI35305870599 passed all23 tests. Evidence saved in
`docs/evidence/phase4_public_observation.md`. Phase4 remains in progress solely
because the real after-close refresh has not yet been observed.

## Exact next actions on continuation

Latest September24 checkpoint supersedes the earlier historical entries below:
public app awake; Phase4 verified. Commits23ea1dd (Phase5),54c5477 (Phase6),
4dccc6f (Phase7). Phase8 implemented/tested locally, acceptance pending. Current
daily code was not executed intraday: CLI correctly skipped. Observe next genuine
after-close run and exact stage status; never mark economics repaired from a
green GitHub job.38 local tests pass. Read AUDIT_HISTORY.md for all open findings.
Check usage first; at09:38 UTC five-hour85% used, weekly13%, five-hour reset
Unix1790259540. No reset credit has been redeemed. Existing daily heartbeat active.

September24: usage reset (weekly2% used at start), daily continuation restored.
Public app woke successfully and displayed September23 data and one INR99,989.11
total at ece92f3. Four scheduled runs succeeded while local work was paused.
Phase4 real-data gate is complete; earlier pending instructions below are historical.
Consolidated audit requested by user: `docs/AUDIT_HISTORY.md`.
Next Phase5: canonical entrypoint and reliable chronological recovery/publication.

September18 after-close continuation checkpoint: fresh usage reached90% weekly
consumed (10% remaining) before manual dispatch. No new workflow was triggered.
Weekly reset: September24 10:44:15 IST. Existing continuation heartbeat moved to
Thursday10:50 IST. On resumption first inspect scheduled runs since this checkpoint;
their evidence may satisfy the real-refresh gate. Restore suitable daily heartbeat
times once usage permits. All accounting repairs remain pending; no phase advanced.

1. Check usage first. If still <=5% in either window, wait for limiting reset.
2. Read this file and AGENTS; inspect Git status and fetch remote without losing edits.
3. After16:30 IST Sep18, trigger the existing daily workflow once via GitHub UI
   (or observe its real scheduled run). No early-time bypass and no synthetic clock
   in production. Workflow URL: https://github.com/Andy7204/dhruva/actions/workflows/daily.yml
4. Inspect exact logs/errors using the AGENTS playbook; pull generated commit,
   verify real ledger/snapshot serialization, both book dates and cache dates,
   Streamlit current commit/date and one NAV. Rerun to prove duplicate safety.
5. Finish Phase4 acceptance documentation/commit. Then Phase5 canonical guarded
   pipeline, Phase6 data safety, Phase7 health, Phase8 watchdog, Phase9 alerts,
   Phase10 failure recovery; remaining phases follow the mission. Repair current
   economics in place as authorized in REPAIR_POLICY.md; update the active-code
   guard rather than creating a second product. Preserve the original archive.
6. Audit issues are explicitly authorized to fix. Preserve original history;
   label legacy imports, recovery/reconstructed days and genuine forward decisions.

Do not spawn new subagents unless user/skill explicitly authorizes it (latest
developer mode). Prior audit agents stopped at usage limits; their durable scripts
and outputs are already saved. Do not restart them unnecessarily.

The earlier challenge study is separate:
`research/results/REPORT.html`; no candidate was deployed. Its current cache no
longer matches its recorded input hashes after the daily refresh; preserve the
original Git history and reconstruct those exact inputs before an exact rerun.
