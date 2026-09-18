# Production observation — 2026-09-17 17:38 UTC

Read-only browser observation of https://dhruva-andy7204.streamlit.app/.
The deployed app rendered successfully. It showed:

- Outer Total value ₹99,914, Return -0.1%, Started with ₹100,000.
- Embedded report: started 2026-09-16, Day 2, updated 2026-09-17.
- Embedded report total value INR99,964: inconsistent with outer NAV by ~₹50.
- Pending simulated BUY INDIGRID ~INR6,825; GOLDBEES and LIQUIDBEES fills.
- Risk-off, next review in approximately 62 trading days.
- False text that costs and tax are both set aside from net worth.
- Backtest heading separate, but false/overconfident claims: 'never saw the future',
  'survivorship-robust', and ~5 years for 2022-09-30 through 2026-09-16 (<4 years).
- No pipeline run timestamp, source commit, strategy version, explicit health
  classification, or freshness warning.

This demonstrates deployment and dated content, not trustworthy daily operation
or genuine after-close historical valuation. The morning manual run processed
September 17 before its market close. The evening refresh updated cached quotes
and the embedded report but did not recompute the already-processed book NAV.
