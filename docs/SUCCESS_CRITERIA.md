# Success criteria — fixed before results

Set September29, 2026, when forward history had three observations and no
verdict was possible. The numbers live in `config.json` under `success_criteria`;
the app applies them with `dhruva.presentation.success_status`.

## Question

Does Dhruva's recorded paper NAV, after modeled costs and tax reserve, beat simply
holding the Nifty 50 through NIFTYBEES by enough to justify its complexity?

## Benchmark

NIFTYBEES.NS quoted close. The ETF keeps constituent dividends inside its NAV
(vendor adjusted close equals close for 2021–2026, so no ETF distributions), so it
tracks the Nifty 50 Total Return Index less about 0.04% a year. The Nifty price
index is still shown, but it omits roughly 1.3% a year of dividends and is not
used for the verdict. The benchmark is shown before any tax an investor would pay
on selling it; the paper books carry a tax reserve. That tilts the test slightly
against Dhruva, which is deliberate: a pass should be clear.

## Rules

Measured from the first forward row (the corrected starting point) with a
NIFTYBEES value. Only recorded NAV counts; the 4% LIQUIDBEES and idle cash
income scenarios are shown separately and never count toward a pass.

| Verdict | Condition |
| --- | --- |
| FAIL (any time) | Worst paper drawdown exceeds 25% |
| FAIL (after 1 year) | Cumulative return trails NIFTYBEES by 15 percentage points or more |
| PASS (after 3 years) | Annualized return beats NIFTYBEES by at least 2.0 points, drawdown within limit |
| FAIL (at 5 years) | PASS condition still not met |
| INCONCLUSIVE | Anything else |

Why these numbers: the strategy rebalances about four times a year, so three
years is roughly twelve decisions, the minimum for a first read. Two points a
year is a margin that covers model error in costs and tax. 25% matches the
existing circuit-breaker level. Missing vendor benchmark values are skipped,
never treated as zero.

## Change log

Changing a rule after seeing results weakens the test. Record every change here
with the date, the reason and the results visible at the time.

- 2026-09-29: initial proposed defaults set; owner may adjust before results accumulate.
