# Strategy search v2 — index strategies on official NSE Total Return data

Started September29, 2026 after the stock-picking strategy (v1) lost to simply
holding Nifty over 2009–2026 (see `research/results/LONG_WINDOW.md`).

## Why index data

v1 backtests picked stocks from today's Nifty-500 list, which carries heavy
survivorship bias (today's list bought and held returned 26% a year since 2009).
v2 uses official NSE Total Return Indices from niftyindices.com. Index membership
is point-in-time and dividends are reinvested, so there is no survivorship bias,
and each index can be bought through an ETF or index fund.

## Honest limits

- **Back-calculated history.** Factor indices were launched recently; values before
  launch are NSE's own back-calculations of rules designed with hindsight. Launch
  dates: Alpha 50 2012-11-19, Low Vol 30 2016-07-08, Alpha Low-Vol 30 2017-07-10,
  Quality 30 2018-04-18 (press report), Momentum 30 2020-08-25, Midcap150 Momentum
  50 2022-08-16, Value 30 2024-06-12. The "live" columns use only post-launch data.
- **Cash** is modeled at a flat 6% a year (no free official overnight-rate history).
- **Gold** is international gold x USDINR until GOLDBEES exists (2009), then GOLDBEES
  with its December 2019 split glitch removed. **Nasdaq-100** is a price index in
  INR, so dividends are missing (conservative).
- **Tax** is simplified Indian FIFO tax without the INR1.25 lakh exemption; 30%
  slab for non-equity short-term gains. Every metric uses liquidation value.
- 24 candidates were tested; the best of many looks better than its future. Shifting
  review dates by up to 15 sessions is part of the robustness check.

## Method

`fetch_indices.py` downloads data; `strategies.py` holds the 24 pre-registered
candidates with standard literature parameters (registration changes are listed
there); `run.py` evaluates each on 2007-10 to today, on a design period before
2016, on a 2016 holdout, on rolling 3/5/10-year windows against Nifty 50, and on
each strategy's live period since launch; `robustness.py` shifts review dates and
doubles costs. Results: `results/scorecard.csv`, `results/results.json`,
`results/robustness.json`.

## Result summary (after ETF costs and tax, INR10 lakh start, 2007-10 to 2026-09)

Rerun after fixing a one-day look-ahead: US-traded series (Nasdaq-100, world gold)
now enter on the next Indian date.

| Strategy | CAGR | Max DD | Sharpe | Sortino | Live CAGR (since) | Nifty 50 same period | Review-date offsets / 2x costs |
|---|---:|---:|---:|---:|---|---:|---|
| Midcap Momentum 50 70% + gold 30%, yearly | 17.8% | -49% | 0.90 | 1.25 | 18.5% (2022-08) | 6.5% | 17.4–17.6% |
| Midcap150 Momentum 50, buy and hold | 17.3% | -70% | 0.66 | 0.89 | 14.8% (2022-08) | 6.5% | 16.9–17.3% |
| Momentum 30 60% + gold 20% + Nasdaq-100 20%, yearly | 15.3% | -45% | 0.78 | 1.06 | 17.1% (2020-08) | 11.8% | 15.0–15.2% |
| Accelerating dual momentum, monthly | 13.4% | -52% | 0.53 | 0.70 | 21.5% (2022-08) | 6.5% | 13.9–18.8% (fragile) |
| Nifty 50, buy and hold (benchmark) | 8.6% | -57% | 0.24 | 0.32 | — | — | 8.2–8.6% |

Full table: `results/scorecard.csv`. The 2008 crash dominates the drawdowns. No
candidate reached 20% a year after tax over this window, which starts at the 2007
peak. Accelerating dual momentum's result depends mainly on which week it reviews,
so it is tracked as a fragile, aggressive book.
