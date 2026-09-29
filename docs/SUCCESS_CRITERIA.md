# Success criteria — fixed before results

Set September29, 2026, before the forward test started. Numbers live in
`config.v2.json` under `success_criteria`; `dhruva/performance.py` applies them.

Each book (A, B, C) is compared with Nifty 50 buy-and-hold run by the same
engine: same start, ETF costs, Indian tax and liquidation value.

| Verdict | Condition |
| --- | --- |
| FAIL (any time) | Worst drawdown deeper than 35% |
| FAIL (after 1 year) | Cumulative return trails Nifty 50 by 15 percentage points or more |
| PASS (after 3 years) | Annualized return beats Nifty 50 by at least 3.0 points, drawdown within limit |
| FAIL (at 5 years) | PASS condition still not met |
| INCONCLUSIVE | Anything else |

Why: yearly-rebalanced books make few decisions, so three years is the minimum for
a first read. Backtests claim 7–9 points a year over Nifty 50; demanding 3 leaves
room for backtest optimism while still requiring a clear edge. 35% is well above a
normal correction but below the 45–50% backtest drawdowns of the 2008 crash, so a
2008-style fall would fail a book, deliberately.

## Change log

Changing a rule after seeing results weakens the test. Record every change with
the date, the reason and the results visible at the time.

- 2026-09-29: initial criteria for v2 books A, B, C (replaces the v1 criteria).
