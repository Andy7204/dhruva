# Dhruva challenge study

Window: 2022-10-03 to 2026-09-15 (975 sessions after warmup).

The criticisms identify real trade-offs, but faster reactions did not consistently improve this sample. Current policy returned +75.37% with -10.92% worst drawdown under audited research execution. The 100-day gate improved full-window return to +83.57% but lagged in the fresh-start final year. The same-ETF control supports the timing objection: index holding returned +40.53% versus +24.28% with a quarterly 200-day gate. Dhruva's stock selection and defensive allocation cannot be conflated with the benefit of the gate. A different satellite reduced drawdown in this sample, with somewhat lower total return. The data are too short and biased to establish a universally superior rule or justify automatic deployment.

Baseline = current policy with audited research execution, not an exact replay of the dashboard.

## Full-window scorecard

| Rule | Net return | CAGR | Worst drawdown | Average cash | Fees INR | Tax INR | Fills |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current policy: 200-day / quarterly | +75.37% | 15.28% | -10.92% | 51.9% | 8,775 | 21,586 | 414 |
| 100-day gate / quarterly | +83.57% | 16.62% | -11.83% | 50.5% | 10,113 | 19,635 | 492 |
| 50-day gate / quarterly | +47.09% | 10.26% | -9.73% | 59.2% | 8,142 | 11,305 | 409 |
| 200-day gate / monthly | +42.18% | 9.32% | -12.05% | 47.3% | 20,218 | 13,089 | 1041 |
| 200-day gate / extra crossing reviews | +39.87% | 8.87% | -14.96% | 48.0% | 18,692 | 14,782 | 974 |
| No market gate / quarterly | +58.25% | 12.32% | -14.52% | 41.9% | 11,762 | 13,380 | 589 |
| 70% current core + 30% dip buying | +60.96% | 12.80% | -8.73% | 56.4% | 5,669 | 16,692 | 238 |
| 70% current core + 30% index holding | +72.21% | 14.75% | -9.43% | 34.9% | 5,694 | 16,730 | 236 |
| 100% NIFTYBEES buy and hold | +40.53% | 8.99% | -15.14% | 0.8% | 328 | 0 | 2 |
| 100% staged NIFTYBEES dip buying | +3.10% | 0.78% | -3.53% | 85.9% | 285 | 0 | 4 |

## 1. Is the 200-day filter too slow?

The 100-day gate returned +83.57% and the 50-day gate +47.09%, versus +75.37% for 200 days. Removing only the market gate returned +58.25%. At upward crossings, the rebound from the preceding risk-off episode's low had already ranged from 0.51% to 9.25% (median 2.34%). Those lows are identified retrospectively for attribution, never used as buy signals. Shortening the market filter does not remove the individual-stock 200-day filter or the core allocation’s 50/200-day votes. No valuation/fundamentals test was possible: a moving average cannot establish cheapness.

## 2. Does the quarterly review add damaging delay?

Monthly reviews returned +42.18% with -12.05% worst drawdown; extra reviews on both crossing directions returned +39.87% with -14.96% drawdown. 12 upward 200-day crossings occurred. Among crossings with a subsequent scheduled review in the sample, the median wait was 32 sessions (maximum 62). Nifty moves from the crossing close to that review ranged from -6.59% to +6.48%. This measures scheduling delay, not guaranteed missed profit: some crossings reversed before the review, and stock eligibility, cash availability and circuit breakers can still block purchases.

## 3. Does the 70/30 split diversify timing?

Both original books share the same gate and quarterly calendar. A dip-buying satellite returned +60.96% with -8.73% drawdown; an always-invested index satellite returned +72.21% with -9.43% drawdown. These alternatives change both timing and stock selection, so their differences are not pure timing effects. They do provide genuinely different entry behavior from the core; this is not a claim of uncorrelated returns.

## 4. How expensive are waiting and trading?

The current-policy baseline averaged 51.9% cash versus 0.8% for index holding. Its modeled fees were INR 8,775, slippage INR 2,155, and total tax INR 21,586, including terminal exit. The friction table reruns the rules because costs and tax change available capital and later decisions; column differences are not a pure additive fee attribution. Cash earns zero; defensive asset gains/losses remain in NAV. A buy-and-hold comparison captures a combined opportunity-cost, asset-selection and risk difference, not cash drag alone.

## 5. Which price paths favor buying dips?

The invented examples isolate the mechanism using one ETF and the same execution/accounting. The dip rule deploys thirds at -10/-20/-30% from a known peak, and exits when that peak is recovered. A quarterly trend rule can avoid an entire choppy path, but can miss a recovery too. Daily trend reviews can lose on false crossings. Buying a dip does not require buying exactly at the bottom, but it can keep adding exposure to a prolonged decline. These outcomes are sensitive to the explicit path and rule; no probabilities are inferred.

## Supplemental same-asset timing control

Added after the primary matrix to separate timing from asset selection; no optimized parameters.
| Rule | Net return | Worst drawdown | Average cash |
|---|---:|---:|---:|
| Index buy and hold | +40.53% | -15.14% | 0.8% |
| Index staged dip buying | +3.10% | -3.53% | 85.9% |
| ETF_200_63 | +24.28% | -20.32% | 29.5% |
| ETF_200_1 | +22.17% | -14.73% | 36.5% |
| ETF_100_63 | +17.69% | -13.70% | 26.6% |
| ETF_50_63 | +21.56% | -11.57% | 45.8% |

## Limits and reproducibility

# Dhruva challenge study â€” fixed before viewing results

Question: does avoiding weakness compensate for missed rebounds, and does the
70/30 construction diversify that timing risk? This is retrospective research,
not a strategy-selection or investment recommendation. Production remains unchanged.

## Comparisons

Start each alternative with INR100,000. The 70/30 variants start actual independent
INR70,000 and INR30,000 books; there are no free daily transfers or rebalances.
Compare the existing 200-day market gate / 63-session review policy with 100- and
50-day gates, 21-session reviews, extra reviews on either direction of a 200-day
crossing, and no benchmark entry gate. Individual stock momentum and 200-day
eligibility remain fixed, so the faster-gate variants isolate the MARKET filter.
The adaptive core allocation still uses the existing 50/200-day regime votes.

Replace the satellite with either a continuously held NIFTYBEES position or a
staged NIFTYBEES dip rule; also run those ETF rules on the entire INR100,000.
Dip rule: deploy thirds of available cycle cash at benchmark drawdowns of 10%,
20%, and 30% from the highest observed close since the beginning of the cache.
Freeze that peak at the first purchase signal. Sell at the next open after the
benchmark regains that peak. No external contributions, leverage, or hindsight
bottoms. If multiple thresholds are crossed together, buy the corresponding
tranches together. Cash earns zero. This tests a specific rule, not every
possible dip-buying strategy. Index comparisons also change asset selection.

## Data and execution

Use supplied Yahoo caches only; report exact hashes, coverage, rejected rows and
the common end date. Use benchmark trading sessions and 260-session warmup.
End at the earlier of benchmark / NIFTYBEES coverage, avoiding the current
partial session. No backward filling or future-based constituent inclusion.
Use current Nifty-500 constituents and repeat on current Nifty-100: both retain
survivorship bias. This is not a point-in-time constituent database. Sector maps
also reflect today's classifications. The window excludes 2008 and 2020.

Reject only contemporaneously invalid OHLC rows, never centered rolling filters.
Signals use current/past closes, pending orders use the next available open.
Missing closes are marked at last observed close, never cost basis. Suspended /
delisted outcomes are not reconstructed. Integer quantities use adjusted-price
units: a split/dividend-adjusted research proxy, not historical share accounting.
ATR is calculated on adjusted OHLC to match those units. Stops gap through at the
worse of the open or pre-existing stop, with sell slippage. Stock buys can trigger
their predetermined stop later that session; OHLC has no intraday path detail.
Proceeds become spendable the next benchmark session (T+1 approximation).

## Costs and tax

Reuse the configured Groww delivery cost function for every stock/ETF fill and
12-bp per-side slippage. This inherits its approximate ETF/instrument treatment.
Use FIFO lots for realized gains and the supplied tax model, shared across books
so annual exemptions are not doubled. Reserve its accrued liability against cash
and subtract it from NAV. Reserve is apportioned by initial book capital; no cash
borrowing between books. Tax rules are a CONSTANT MODEL across the whole period,
not historically correct statutory rates. Loss set-off, surcharge/cess, dividend
slab tax and InvIT distribution components are not fully modeled. Adjusted prices
approximate reinvested distributions; they cannot prove real after-tax wealth.

Report final wealth AFTER an estimated liquidation at the last observed close,
including exit slippage, fees and resulting tax. This is a terminal valuation
adjustment, not a same-day-close trading signal. Show pre-liquidation marked NAV
too. Daily/yearly paths are tax-reserved marked NAV; final return/CAGR and worst
drawdown include terminal liquidation. Sharpe uses zero risk-free rate.
Run no-friction, fees/slippage-only and doubled-friction checks without tuning.

## Validation and interpretation

Freeze variants before results. Repeat quarterly phase offsets 21 and 42 sessions;
report a fresh-start final 252-session period plus overlapping rolling one-year
returns. These are robustness checks, NOT truly untouched out-of-sample evidence:
the original project was developed using this history. Do not choose a winner
from the best parameter. Test prefix invariance, next-open gaps, T+1 restrictions,
tax NAV subtraction/shared exemption, and synthetic rebound/continued-decline/
choppy paths. These paths explain mechanisms, not empirical probabilities.

Research engine departs from deployed code deliberately in execution/accounting:
no centered cleaning, adjusted ATR, gap-aware stops, settled-cash constraint,
FIFO tax, tax-reserved NAV, actual separate books, no defensive assets accidentally
ranked as stocks in the aggressive book, and no cost-basis marking of missing
quotes. Thus label the baseline 'current policy, audited research execution',
not an exact replay or validation of displayed historical dashboard returns.


Commands: `python research/test_challenge.py`; `python research/challenge.py`; `python research/scenarios.py`; `python research/make_report.py`.