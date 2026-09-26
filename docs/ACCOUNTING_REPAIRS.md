# Initial paper-accounting repairs — September25,2026

Phase3 remains in progress. Implemented and unit-tested core repairs:

- Permanent order journal; persisted namespaced identities, explicit cancellations,
  next-session-only fills, duplicate-day no-op and missing held-price rejection.
- Gap stops use the worse of opening price and stop before slippage. Delivery-only
  model does not sell unsettled purchases; no BTST, margin or intraday assumption.
- Sales create NAV-bearing receivables, not spendable cash. T+1 payout is credited
  at settlement-day end; earliest reuse is the following session's open. This is
  deliberately conservative about payout timing. Separate clearing calendar is
  verified only September–October2026 and fails closed outside coverage.
- Economic FIFO per virtual sleeve; shared taxpayer FIFO across both sleeves.
  STT remains an economic expense but is excluded from deductible tax basis.
- Shared FY exemption, short/long loss setoff and eight-year carry assuming timely
  returns, configured slab,4% cess and0% assumed surcharge. No external income,
  basic exemption/rebate or unrelated investments inferred. Setoff allocation is
  deterministic: LT losses first, higher-rate eligible gains first, then exemption;
  this is a conservative model, not tax optimization or a filing engine.
- NAV and purchase cash subtract allocated tax reserve. Reserve is not represented
  as a tax payment. Capital gains in prior years remain reserved until payment is
  explicitly modeled. Allocation is bookkeeping attribution across one owner.
- Explicit instrument taxonomy independent of allocation. Listed commodity funds,
  specified debt funds and business trusts differ. Current-period tax rules are
  not retroactively claimed valid for all historical research years.
- Modeled Groww DP20 plus GST, IPFT, and ETF STT exceptions. Rounded paper charges
  are not a broker contract note. Rate assumptions are resident/default account.
- Stock position/sector count and entry weight caps, cost-distance screening,
  minimum-hold routine exits. Breaker can reset after63 completed sessions with
  market trend on, reanchoring peak and forcing review, or on NAV recovery. This
  explicit policy fixes the all-cash deadlock; it was not selected by optimization.

Reconciliation (`python -m dhruva.reconcile`, then `--apply`) preserves original
September16 intents and uses original immutable daily snapshots. September17
uses the first later captured snapshot for its corrected close: this is expressly
reconstruction, not evidence that final prices were known during the original run.
The same82 gold and3 liquid units remain. Corrected latest fees20.41 versus33.60
increase September24 NAV by13.19; September17 also corrects unfinished valuation.
Original segments are never replaced. A new CORRECTION event references old
events, current producing commit/config and source snapshots. Repeated daily
capture resolves the newest correction bundle, not the superseded original.

## Verified primary sources

Retrieved September25,2026:

- [NSE clearing cycles](https://www.nseclearing.in/equities) and
  [CM settlement holidays](https://www.archive.nseclearing.in/content/circulars/CMPT71904.pdf).
  Text table checked; web PDF screenshot retrieval failed. Debt-segment circular
  found initially was not used as authority for equity settlement.
- [Groww pricing](https://groww.in/pricing): brokerage, DP, GST, IPFT and standard
  equity charges. [Groww STT](https://groww.in/help/stocks%2C-f%26o%2C-ipo-%26-mtf/sx-pricing/what-is-stt).
- [Income Tax Department capital gains](https://www.incometaxindia.gov.in/w/capital-gain)
  and [AMFI fund tax treatment](https://www.amfiindia.com/investor/knowledge-center-info?zoneName=TaxRegimeForMutualFunds):
  holding periods, instrument classes, specified-debt-fund treatment and STT basis.

## Still required before Phase3 completion

Distribution/dividend income and slab-tax handling, adjusted-price versus actual
share reconciliation, stronger end-to-end risk stress checks, deployed corrected
state verification and a genuine after-close run under the repaired code. Current
Yahoo cache does not establish all LIQUIDBEES distributions; do not invent them or
call the NAV a fully after-tax actual-rupee return. Health retains explicit model
warnings. Phase4 must align and rerun backtests instead of reusing old returns.

### Confirmed distribution blocker (September25 evening)

The [fund's scheme document](https://mf.nipponindiaim.com/InvestorServices/SIDETF/NipponIndia-ETF-Nifty-1D-Rate-Liquid-BeES.pdf),
page32, specifies daily compulsory IDCW reinvestment, including weekend accrual,
and fractional units to three decimal places. Exchange sales use whole units;
fractional redemption is a separate facility. Retrieved September25,2026.
Therefore flat price/NAV observations do not demonstrate zero investment income.
The currently modeled three LIQUIDBEES units exclude unverified distributions.
Do not estimate them from a quoted annual yield or silently treat unknown income
as zero. Required repair: sourced dated declarations, entitlement/allotment
records, fractional inventory and taxable-income reserve, with no double count
of adjusted-price returns. Current integer-lot checks intentionally describe
exchange-purchased inventory only, not certification of distribution completeness.

Income liability support now accepts explicit `income_receipts` (book/id/gross/
taxable_date). Configured `income_slab_pct` defaults to the existing30% slab;
cess/surcharge apply. Capital losses and the equity LTCG exemption cannot offset
this income. It participates once in shared reserve/NAV reconciliation. No
production receipt has been inferred or posted: receipt ingestion, fractional
allotment inventory and raw-unit execution integration remain required. TDS must
be represented as prepaid tax rather than reducing taxable gross income.
[Broker tax explanation](https://support.zerodha.com/category/console/reports/taxation/articles/dividends-on-liquid-etfs-and-liquid-bees)
retrieved September25 corroborates slab taxation and allotment-value cost basis.

### September26 implementation

Live fills and marking now use quoted OHLC, leaving adjusted features to the
deterministic signal layer. ATR stop distances are converted to quote units.
Legacy held positions can migrate only when prior quoted/adjusted prices agree;
changed previously recorded raw quotes require explicit corporate-action repair.
This is a fail-closed corporate-action guard, not an automatic split processor.

`qlab.income.post_receipt` posts evidenced cash or fractional-unit receipts
atomically. Config `income_receipts` is processed after fills, before shared tax
and final NAV. It requires book/id, gross/withheld, effective/taxable dates,
retrieval timestamp, HTTPS source and SHA256. Future data cannot be used; a late
Daily ingestion additionally requires `source_path` within the project and verifies
its bytes against the SHA256 before posting. A hash string alone is insufficient.
amendment to an already recorded session requires explicit ledger correction.
Weekend events may enter the next unprocessed session. TDS is a prepaid-tax asset;
gross income is taxed once, with net unpaid tax restricting available cash.
Reinvested lots retain allotment basis; exchange sales remain whole units while
fractional remainders remain owned. Allotment units/net proceeds must reconcile.

No calculator-derived income is posted yet. The September26 query through26
still returns only rows through24. Missing25 is unknown, not zero. Receipt source
ingestion, pending accrual versus actual allotment reconciliation and forward
deployed acceptance remain outstanding;70 tests passed before the additional
fractional FIFO remainder regression, which also passed in the focused suite.
