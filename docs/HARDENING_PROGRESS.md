# Dhruva hardening checkpoint

Mission: [HARDENING_MISSION.md](HARDENING_MISSION.md). Follow phases 0–25 in order.
Read AGENTS.md fully before resuming. Paper research only; deterministic decisions;
preserve existing history and distinguish imported records from prospective evidence.

## Current checkpoint

- Phase 0 audit complete. Engineering and quantitative audits reproduced defects
  without running the production pipeline or changing live records.
- Local source checkpoint: `94287c7` (isolated strategy challenge study saved).
- Last deployed daily-data commit: `75dd97e`; production source originally `ee7531d`.
- Public repository: https://github.com/Andy7204/dhruva
- Public app: https://dhruva-andy7204.streamlit.app/
- GitHub scheduled run `35252434924` succeeded September 17, 2026,
  17:23:24–17:28:32 UTC. Scheduled cron was 13:00 UTC; actual dispatch was late.
- Do not correct execution/accounting before freezing v1 in Phase 1.
- Do not mark a phase complete until implemented, tested, demonstrated and committed.
- No later phases are complete yet.

## Continuation and usage

- User authorized continuation until all tasks are complete, including after resets.
- Thread heartbeat ID: `continue-dhruva-hardening-after-usage-reset`, hourly.
- Local continuation requires this computer and Codex to remain running. GitHub daily
  execution is independent of the local computer.
- Check fresh usage at phase boundaries. At <=10% remaining in either core window,
  checkpoint exact next action and limiting reset, then defer until capacity returns.
- Last check September 18: five-hour usage 9% (91% left), reset Unix 1789721187;
  weekly usage 67% (33% left), reset Unix 1790226855. Fresh checks take precedence.
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
| 4 | In progress | Implement deployed freshness/failure behavior; hardened after-close refresh still required for combined gate before Phase5. |
| 5–10 | Not started | Canonical pipeline, data, health, watchdog, alerting, failure recovery. |
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

The earlier challenge study is separate:
`research/results/REPORT.html`; no candidate was deployed. Its current cache no
longer matches its recorded input hashes after the daily refresh; preserve the
original Git history and reconstruct those exact inputs before an exact rerun.
