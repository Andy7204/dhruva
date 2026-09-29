# Prospective paper-income sensitivity model

Authorized September29, 2026. This is an assumption-based companion to the
recorded paper books, not an AMC distribution receipt or a new strategy.

- Fixed illustrative annual rate: 4%, not an observed yield or prediction.
- Base: INR1,000 per LIQUIDBEES unit settled at the previous recorded close.
- Simple ACT/365 from September30 close; weekends and holidays accrue using
  that previous-close exposure. No compounding, reinvestment or fractional allotment.
- Modeled tax uses configured income slab (fallback: nonequity short rate),
  surcharge and cess. No TDS credit or actual payment is inferred.
- Persisted gross, tax and net are separate `income_scenario` fields in the
  existing books/ledger. They do not affect cash, inventory, NAV, calls or returns.
- No historical backfill. Same-day retries cannot add income again. Missing days
  follow the normal recorded recovery process; no invented observation timestamps.

The dashboard labels this estimate separately. Verified receipts continue through
the source-hashed receipt path. Do not add scenario amounts to verified receipts
or present the scenario as performance. Unknown credit dates and rounding need no
guess for this model because it does not create credited units.

## Calendar maintenance

`special_sessions` in the trading calendar accepts date keys with an official
`source_url` and `completed_after_ist` (close plus vendor buffer). Both the daily
guard and freshness calculation honor this time, including weekend sessions.
Weekend workflow checks at23:30IST skip normal closed days. Extend coverage only
after reviewing the official circular and adding its timing; no November8 timing
has been invented. Ordinary trading currently endsNovember7, clearing December31.
