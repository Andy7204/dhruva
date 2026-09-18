# Phase 4 — deployment verification

Provider: Streamlit Community Cloud. Repository Andy7204/dhruva, branch main,
entrypoint streamlit_app.py. The public UI is a read-only view of committed
state. No database or durable writes depend on its ephemeral filesystem.
No user-supplied app secret is required. Requirements follow the pinned lock.

The app now renders one saved portfolio total, never a sum revalued from later
quotes beside an older NAV. Every configured book must parse, match configured
capital, contain a finite value and agree on date. Otherwise totals are withheld.
Legacy reports/dashboard.html is preserved but not embedded: it contains audited
false accounting/trust claims. Later UX phases can expose corrected simulations.

Health shows deployment commit, strategy version, recorded portfolio date,
latest benchmark date, expected completed session, last pipeline attempt and
last completed hardened pipeline. When no completed pipeline is recorded, it
says so rather than inventing a timestamp. Morning no-run is not market no-signal.
The page refreshes health every60seconds while active; no cached health result
can keep a stale success visible indefinitely. V1 remains DEGRADED even with
current data because its tax, settlement and execution defects remain unresolved.

Tests: 23 pass locally, including actual Streamlit AppTest execution, stale and
failed UI rendering, corrupt/missing totals, intraday dates, ledger persistence
and frozen source verification. Synthetic tests modify no real book records.

## Acceptance still pending

Remote browser must verify the deployed new page, commit and unified NAV.
The next actual after-close run must refresh data and publish output. The morning
manual run deliberately skipped it; do not misreport that as a fresh data test.
Historical scheduled execution was verified, but this hardened path has not yet
been observed after market close. Only then can the combined Phase3–4 gate pass.
Phase5 and the new accounting version must not be marked started before this gate.
