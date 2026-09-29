# Long-window rerun, 2009–2026

Run September29, 2026 by `research/long_window.py`. Full numbers are in
`long_window.json`; the rows removed as vendor glitches are listed in
`long_window_repairs.json`. Same rules and research execution as the 4-year
study, with one change: the circuit breaker also releases after 63 sessions
with the market trend on, as production does. Without that rule the research
simulator stayed in cash from about 2016 onward.

Window 2009-01-05 to 2026-09-29, 4,352 sessions, INR100,000 start, after
modeled costs and tax including terminal liquidation.

| Rule | CAGR | Worst drawdown | Average cash |
|---|---:|---:|---:|
| Current policy (200-day, 63 sessions), Nifty-500 | 8.72% | -35.96% | 50.4% |
| Current policy, Nifty-100 | 8.50% | -29.70% | 44.6% |
| No market filter, Nifty-500 | 11.71% | -27.59% | 41.1% |
| No market filter, Nifty-100 | 12.28% | -22.65% | 33.1% |
| 70% core + 30% index | 10.71% | -28.49% | 27.0% |
| NIFTYBEES buy and hold | 12.01% | -36.25% | 0.4% |
| Survivor control: equal-weight today's Nifty-500 stocks, held (pre-tax) | 26.28% | -38.99% | 0% |

Fresh 4-year accounts (CAGR): 2010–13 policy 5.0% vs index 4.5%; 2014–17 16.5%
vs 14.3%; 2018–21 11.1% vs 15.1%; 2022–25 9.2% vs 10.2%.

Reading: over 17 years the current policy trails simply holding NIFTYBEES by
about 3.3 points a year with a similar worst drawdown. The market filter is the
main drag: removing it recovers most of the gap. The survivor control shows how
much hindsight today's constituent list contains; every stock-picking result
here is inflated by it, so the true gap to NIFTYBEES is probably wider.
Idle cash earns zero here; at a liquid-fund yield, 50% average cash would add
roughly 2–3 points before tax, still not clearly above NIFTYBEES.

Limits: current constituents (survivorship), only 271 stocks priced at the 2009
start, Yahoo adjusted prices with logged glitch repairs, research engine rather
than an exact production replay, simplified tax. Not a forecast or advice.
