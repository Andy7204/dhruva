# Independent operational watchdog (acceptance pending)

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

Phase8 is still in progress: a remote workflow execution and external alert path
must be demonstrated. Artifact/log failure alone is not verified notification
delivery. Phase9 will harden that one alert channel. Do not mark either complete
before the actual evidence exists. No Telegram credentials are configured.
