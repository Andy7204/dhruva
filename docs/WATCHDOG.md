# Independent operational watchdog

`python -m dhruva.watchdog` reads committed evidence without fetching prices,
making decisions or touching book/ledger state. A separate GitHub workflow runs
daily at21:00 UTC (02:30 IST), after the preceding session's00:30 IST deadline.
The grace interval acknowledges observed GitHub dispatch delays without treating
an absent run as a valid no-action conclusion. It checks benchmark/portfolio dates,
completed attempt, ledger heartbeat/integrity, corrupt state and explicit failures.

September24 real local check returned operational PASS for September23 and run
35896879641, retaining all accounting warnings. Evidence: runs/watchdog/latest.json.
38 tests pass including missing-run-without-failure-record detection, missing
ledger and a not-yet-due session. Operational PASS is not strategy certification.

This workflow is independent of the daily job but shares GitHub as a scheduler;
a GitHub-wide outage can stop both. It does not poll Streamlit with fake users to
defeat Community Cloud sleep. The dashboard can be woken by a real visitor.

Phase8 remote acceptance passed: normal run36016354838 and synthetic alert
run36016083742. Issue #3 proved actual creation, deduplication and recovery.
See evidence/phase8_remote_acceptance.md for the initial failed test and repair.
Phase9 broad alert coverage remains in progress. No Telegram credentials are needed
for GitHub Issues; the workflow uses its scoped built-in token.
