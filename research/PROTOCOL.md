# Dhruva challenge study — fixed before viewing results

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
