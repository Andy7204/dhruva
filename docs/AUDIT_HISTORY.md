# Dhruva: audit history and error register

Updated 2026-09-24. Paper research only. This consolidates the work since initial
deployment; it is not a claim that every finding is repaired. The original audit
is preserved in [CURRENT_STATE_AUDIT.md](CURRENT_STATE_AUDIT.md). The user's
September18 amendment authorizes repairs **in place**, with original Git/archive
evidence retained and recalculated history identified as reconstruction.

## What was audited, in order

September25 follow-up: numeric comparisons could silently accept NaN in saved
NAV/cost, and aggregate shared FIFO quantities did not validate underlying lots.
Added explicit finite/nonnegative basis and positive integer lot checks, duplicate
lot rejection and saved-NAV finiteness. Corruption regression tests pass. Remote
CI36154285351 separately verifies the corrected dashboard-label test and prior
60-test suite; the new accounting checks require their own published CI result.

1. **Deployment:** repository root, committed state/cache/report, workflow schedule,
   manual execution and public Streamlit rendering. Manual run35184975533 and
   scheduled run35252434924 succeeded. Cron is weekdays18:30 IST; the observed
   September17 scheduled dispatch was over four hours late.
2. **Strategy challenge:** tested the slow200-day gate,63-session review delay,
   common70/30 timing exposure, cash/trading opportunity costs, and dip buying
   under rebound, decline and choppy paths. Fixed protocol,10 primary variants,
   same-ETF timing controls, sensitivity checks and eight research tests.
3. **Full repository audit:** data, features, deterministic rules, execution,
   tax/costs, risk, portfolios, historical metrics, state, scripts, workflow,
   public UX, AI claims, monitoring, alerts and reproducibility.
4. **Bounded defect reproduction:**11 engineering observations (including positive
   controls) and nine quant defect fixtures. No production mutation:2,380 and
   2,415 protected files respectively compared unchanged.
5. **Original evidence protection:**52-file archive, manifest and mutation tests.
   This remains audit evidence; it must not prevent authorized in-place repairs.
6. **Ledger:** hash-linked append-only segments, exact compressed input snapshots,
   stable event identities, correction events, corruption and duplicate tests.
   A fresh remote checkout/restarted process retained the synthetic fixture's
   single event and identical head. Synthetic evidence is excluded from returns.
7. **Operations:** pinned dependencies/actions/Python; serial workflow, timeouts,
   retries, explicit holiday coverage, before-close guard and durable failures.
   A real morning run returned SKIPPED_NOT_DUE rather than recording that session.
8. **Dashboard:** one recorded before-tax value, corrupt/partial totals withheld,
   stale/future dates and failed backend visible, commit/version/timestamps shown.
  23 tests passed locally and in GitHub; deployed rendering observed September18.
9. **September24 continuation:** four additional scheduled runs succeeded on
   September18,21,22,23 and published real input snapshots/ledger segments.
   Public app was asleep due to inactivity; waking it restored the dashboard.
   It displayed September23 data at commit ece92f3 and one INR99,989.11 total.
   All4,016 ledger events/four snapshots verified; repeat capture in a copy of
   real evidence preserved the original result and ledger head.
   Job success alone does not certify accounting, all-symbol data or public UX.

## Error register

Evidence labels: **reproduced** = bounded fixture or observed production behavior;
**inspection** = source-level finding; **limitation** = research/model constraint.
Status describes the latest documented verified scope, not intended work.

| ID | Finding and impact | Evidence | Status |
|---|---|---|---|
| D01 | Centered five-row cleaning lets future rows change past inclusion; `[100,100,200]` rejects the third row but appending `[200,200]` retains it. | Reproduced; `qlab/data.py` | Fixed causal rowwise cleaning; prefix tests pass |
| D02 | Fetch failure returns an old cache as normal data; a2020 fixture was accepted. | Reproduced; `data.py` | Daily gate rejects failed-fetch fallback/stale data; UI warns |
| D03 | Missing symbols are skipped without a complete run-quality contract. | Inspection | Per-symbol exclusions and95% coverage gate added |
| D04 | Held symbol absence crashes stop lookup: `AttributeError: 'NoneType' object has no attribute 'at'`. | Reproduced; `livebook.py` | Daily path blocks missing held input before stepping; direct low-level call remains unsupported |
| D05 | Missing prices can fall back to entry cost; missing regime observations can default risk-on. | Inspection | Daily path rejects missing held prices/regime; legacy engine standalone still needs alignment |
| D06 | Raw ATR is mixed with adjusted prices: ATR4 versus adjusted ATR2. | Reproduced; `indicators.py` | Fixed adjusted ATR/ADX/Donchian; unit test passes |
| D07 | Price caches and corporate-action adjustment vintages change; no historical point-in-time constituent database. | Inspection/limitation | Prospective snapshots added; historical limitation remains |
| D08 | No complete zero-volume, freshness, missing-universe and corporate-action validation contract. Initial cache scan found no duplicate dates/impossible OHLC in that sample. | Inspection | Contract implemented/tested on real cache; independent corporate-action certification remains a limitation |
| E01 | Recovery recomputes inception from latest date, skipping intermediate missed sessions. Sep14 state plus Sep14–17 data steps only Sep17. | Reproduced; `orchestrator.py` | Fixed chronological replay; interruption/recovery test passes |
| E02 | A morning run finalized the date; evening quotes changed while saved NAV stayed unchanged. | Production observation | Guard and append-only initial NAV reconstruction applied September25; original evidence retained |
| E03 | Gap stop can fill at90 when open80/high85/low75: an impossible sale. | Reproduced; `livebook.py`, historical engine | Live gap fill fixed/tested; legacy backtest alignment remains Phase4 |
| E04 | T+1 is a status without cash restriction: zero opening cash still buys990 shares using same-day sale proceeds. | Reproduced | Cash-only receivables implemented/tested; payout credited settlement-day end |
| E05 | Business-day settlement ignores exchange/settlement holidays. | Inspection | Separate clearing calendar verified for September–October2026; expires closed |
| E06 | Old settled fills are pruned from orders, contradicting a complete journal. | Reproduced | Permanent journal implemented; initial pruned orders recovered from immutable seed |
| E07 | Process-local order counter can reuse identities after restart. | Inspection | Persisted namespaced identities and restart regression test |
| E08 | Multi-file overwrites can leave partial book/report state after failure. | Inspection | Ledger-first bundle and projection recovery tested; report failure still visible through failed attempt |
| A01 | Tax accrues without reducing cash availability/NAV: tax2000 still leaves NAV100000. | Reproduced | Shared capital-gains reserve deducts NAV/available cash; distribution tax still pending |
| A02 | Separate books duplicate annual exemption: two100000 gains produce0 versus modeled shared9375. | Reproduced | Single taxpayer FY exemption and exact reserve allocation tested |
| A03 | Average cost/earliest holding date replaces FIFO tax lots. | Inspection | Shared taxpayer FIFO plus per-sleeve economic FIFO implemented/tested |
| A04 | Instrument tax class depends on a book's basket configuration. | Inspection | Explicit instrument taxonomy independent of basket; investor-specific limits documented |
| A05 | Dividend tax at slab is not fully modeled; adjusted-price units do not reconstruct actual historical share/dividend accounting. | Limitation | Pending explicit treatment/disclosure |
| P01 | Empty aggressive basket admits GOLDBEES as an equity momentum pick. | Reproduced | Daily book config now preserves common defensive exclusions; historical engine alignment pending |
| P02 | Position-weight limits, edge/cost checks and exit behavior differ between live and backtest. | Inspection | Pending |
| P03 | All-cash circuit breaker can remain unable to recover. | Inspection | Explicit63-session cooldown plus trend recovery fixes cash deadlock; no return-based tuning |
| P04 | Both books share200-day market gate and63-session cadence;70/30 does not diversify entry timing. | Inspection/research | Trade-off documented and tested; no winner deployed |
| B01 | Historical engine uses same-day-close fills and pre-tax results versus live next-open execution. | Inspection | Disclosed; alignment pending |
| B02 | `compare3.py` blends daily returns as if70/30 rebalanced free every day rather than separate live accounts. | Inspection | Pending; challenge study uses separate accounts |
| B03 | Whole-period coverage influences benchmark eligibility in `validate.py`. | Inspection | Pending |
| B04 | Current Nifty500 and Nifty100 lists retain survivorship/future-membership bias. | Limitation | Must remain disclosed; large-cap rerun is not bias-free |
| B05 | Walk-forward chaining loses initial/fold-transition friction. | Inspection; `optimize.py` | Pending |
| B06 | Return normalization from first post-trade value hides entry costs; fee summaries omit some open/basket costs. | Inspection; `metrics.py` | Pending |
| B07 | Historical results lack reliable producing commit/config/input provenance; five-year/three-year-live claims exceed evidence. | Inspection | Audit/UI qualifications added; legacy outputs/docs pending |
| B08 |505/506 challenge input cache hashes changed after daily refresh. This proves changed files, not necessarily changed historical rows. | Hash comparison | Exact-input reconstruction required before exact rerun |
| U01 | Public outer total99,914 versus embedded report99,964. | Production observation | Fixed display: one saved NAV; legacy report preserved, accounting still pending |
| U02 | Corrupt aggressive book silently omitted; stale balanced-only fixture showed71,000 without warning. | Reproduced | Fixed UI: reject partial/corrupt totals, show warnings |
| U03 | Missing run time/version/commit/freshness allowed stale output to look current. | Production observation | Fixed UI within current date/operation checks |
| U04 | Report claimed tax set aside, no look-ahead and stronger validation than demonstrated. | Inspection | Removed from public embedded view; legacy generator wording pending |
| U05 | Streamlit Community Cloud hibernates after inactivity. | September24 public observation | Awake and verified; hosting constraint remains |
| O01 | Floating packages/actions made deployments irreproducible. | Inspection | Pinned; clean Linux install and CI verified |
| O02 | Weekday cron lacked holiday/before-close guards. | Inspection | Guard implemented; explicit calendar only through2026-10-31, then fail closed |
| O03 | Cron dispatch can arrive hours late; a green job does not establish fresh complete data. | Remote runs | Disclosed; freshness contract/watchdog pending |
| O04 | No independent missed-run watchdog or reliable failure alert. | Inspection | Independent remote watchdog and actual GitHub issue lifecycle verified |
| O05 | Telegram failure returnsFalse and is ignored. | Reproduced | Result now logged as delivered/failed/not-configured; no successful delivery claimed |
| O06 | No durable structured attempt/failure status. | Inspection | Durable attempts and per-stage transitions implemented/tested |
| O07 | No production reliability suite at baseline. | Inspection |23 production tests added; broader recovery/economics coverage pending |
| O08 | No genuine live benchmark/strict long-running forward-performance proof. | Inspection | Pending; a few paper dates are not a track record |
| L01 | `show_call.py`/news overlay read legacy Sep15 artifacts rather than current books. | CLI observation/inspection | Pending |
| L02 | Reset script targets legacy files and ignores active books. | Dry-run observation | Pending; no reset executed |
| L03 | Packaging excludes `.github` and can include a future `.env`. | Inspection | Pending; not authoritative deployment export |
| L04 | News outage becomes `quiet`; items lack full URL/publication/retrieval provenance. | Reproduced/inspection | Pending |
| L05 | Narrator provider fallback/provenance is insufficiently logged. | Inspection | Pending; LLM still narration only |
| L06 | `learn.py` is unused heuristic weighting, not trained live ML. | Inspection | ML/adaptive claims must be removed or qualified; ML deferred |
| L07 | Configuration prose says50/50 while actual configured accounts are70/30. | Inspection | Contradictory duplicate config note removed;70/30 retained |

## Strategy challenge results (research, not live returns)

Window2022-10-03–2026-09-15;975 sessions. Current constituents, adjusted-price
research units and simplified tax assumptions remain material limitations.

| Variant | Net total return | Maximum drawdown |
|---|---:|---:|
| Current policy200-day /63-session |75.37%|-10.92%|
|100-day /63-session |83.57%|-11.83%|
|50-day /63-session |47.09%|-9.73%|
|200-day /21-session |42.18%|-12.05%|
| Extra reviews on trend crossings |39.87%|-14.96%|
| No market gate |58.25%|-14.52%|
|70% current core +30% dip satellite |60.96%|-8.73%|
|70% current core +30% index holding |72.21%|-9.43%|
| Index buy and hold |40.53%|-15.14%|
| Staged index dip buying |3.10%|-3.53%|

The current-policy research baseline averaged51.9% cash; modeled fees8,775 and
tax21,586 including terminal exit. On the same ETF, quarterly200-day filtering
returned24.28% versus40.53% holding, supporting the missed-rebound objection.
The100-day result did not remain superior in the fresh-start final year.
These are sample-dependent trade-offs, not evidence to deploy a winner.
See [full report](../research/results/REPORT.md) and fixed protocol.

## Evidence and exact errors

- [Engineering probe](evidence/phase0_engineering.json):11 observations.
- [Quant probe](evidence/phase0_quant.json):nine reproduced defects.
- Probe source: `phase0_engineering_probe.py`, `phase0_quant_probe.py`.
- [Original public observation](evidence/phase0_streamlit_observation.md).
- [Archive verification](evidence/phase1_freeze.json).
- [Remote restart/duplicate evidence](evidence/phase2_remote_restart.json).
- [Deployed UI evidence](evidence/phase4_public_observation.md).
- Audit console initially raised `UnicodeEncodeError` for the rupee character;
  the AGENTS playbook's UTF-8 initialization resolved the probe execution.
- Missing held-symbol fixture: `AttributeError: 'NoneType' object has no attribute 'at'`.
- Outage fixture console: `! MOCK.NS: MOCK API unavailable`; old data was returned.
- Older audit prose called JSON results `phase0_*_probe.json`; actual files are
  `phase0_engineering.json` and `phase0_quant.json`, linked correctly above.

## Completion rule

Phases0–7 completed; Phase4 after-close/public acceptance verified September24.
Later phases and accounting repairs are not certified complete. Each repair needs
implementation, relevant tests, observed behavior, documentation and a saved
commit. Keep decisions deterministic, use no future data, model costs/tax honestly,
retain original evidence, and do not rename errors away to make health green.

## September24 evening continuation

- Watchdog and real GitHub issue acceptance passed (phase8_remote_acceptance.md).
- Immediate issue-list lag caused duplicate synthetic alerts; receipt-based lookup
  fixed and regression tested. Synthetic issues1–3 are closed.
- Concurrent source push prevented old daily publication: `main -> main (fetch first)`.
  Safe code-only rebase and full generated-evidence artifact now implemented/tested.
  The failed old run did not preserve its ledger/cache; rerun must use actual time.
- Health now compares current projections with the latest immutable ledger bundle
  and rejects unexpected changes, including same-date partial publication.

September24 latest: mission consolidated to ten phases without dropping scope.
45 tests pass. Public UI at f834426 correctly shows stale Sep23 data. Cookie-aware
actual iframe health endpoint returns200ok; root endpoint is an HTML shell and plain
HTTP client encountered303 loop. Deployment probe corrected to observed iframe URL.
Daily retry36017079889 remains running at usage checkpoint; no success claimed.

## September25 core accounting repair work

Operational Phase2 accepted: daily36017079889 recovered publication; scheduled
36035932204 added zero duplicate evaluations; watchdog36074243248 passed. Public
Sep24 total99882.48 matched both books. Phase3 code/tests now cover E03/E04/E05
(bounded clearing calendar),E06/E07,A01/A02/A03/A04, entry caps and breaker recovery.
Initial corrected history dry run retains82GOLDBEES+3LIQUIDBEES, with13.19 less
modeled cost after ETF-STT correction/IPFT. Applying/publishing correction and
remaining distribution income/adjusted-unit checks are separate acceptance work.
Taxonomies, shared FIFO across sleeves, reserve attribution and policy assumptions
are documented in ACCOUNTING_REPAIRS.md; do not call the whole phase complete.
