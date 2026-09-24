# Quant Lab — an honest INR momentum + diversification research system

## Hardening status

The [current-state audit](docs/CURRENT_STATE_AUDIT.md) found material correctness
and reliability defects in the original implementation, including tax reserves,
settlement cash, missed-session recovery and stale-data display. Earlier claims
below describe the original project and are not evidence those defects are fixed.
Only two original live dates were recorded at audit; historical simulations are
not a multi-year live track record. Follow [verified progress](docs/HARDENING_PROGRESS.md).

The [original v1](strategies/dhruva_v1/README.md) is archived with its known flaws.
The daily entrypoint checks its economic source/configuration hashes before work.
Per the user's September18 direction, execution/accounting corrections will fix
the existing app and paper books in place. The archive is evidence, not a separate
active product. See [repair policy](docs/REPAIR_POLICY.md); recalculations will be
identified honestly and the current health label will change when checks pass.

The [paper ledger](docs/LEDGER.md) preserves evaluation provenance and exact
captured portfolio bundles. Restart, duplicate, corruption and remote-checkout
tests pass. This protects evidence; it does not cure v1's accounting limitations.

Daily runs now record operational attempts and reject intraday processing. The
[workflow audit](docs/WORKFLOW_AUDIT.md) documents scheduling, dependency pins and
remaining limits. Calendar coverage is bounded and must be reviewed before expiry.

The public page now uses one saved portfolio valuation and displays explicit
health, dates and commit provenance. Corrupt books withhold totals; stale data
and failed runs display errors. V1 remains visibly degraded while its economic
defects are corrected in place. Legacy HTML is preserved as evidence,
but no longer embedded as a second, conflicting live valuation.

## Strategy challenge study

`research/` contains an isolated comparison of market-filter speed, review delay,
alternative satellite rules, index holding and staged dip buying. See
[research/README.md](research/README.md) for reproduction and
[the full report](research/results/REPORT.html) for results and limitations.
It uses next-open execution, modeled costs/tax and separate 70/30 books; its
audited research execution differs from the original dashboard backtest.
It does not change the deployed strategy or live paper books.

## Public dashboard deployment

Use this folder as the repository root. `streamlit_app.py` displays the committed
dashboard on Streamlit Community Cloud. `.github/workflows/daily.yml` refreshes
the paper books, reports, and cached prices at 13:00 UTC (18:30 IST) on weekdays
and supports manual runs. See [DEPLOY.md](DEPLOY.md) for setup.
Optional Actions repository secrets are `TELEGRAM_TOKEN` and `TELEGRAM_CHAT` for
alerts, and `ANTHROPIC_API_KEY` for LLM narration without an OpenAI key.
`OPENAI_API_KEY` is an alternative; with no key the rule-based narrator runs.
Narration never changes the deterministic trading decisions.

The current architecture and limitations are documented in [AGENTS.md](AGENTS.md):
live orders fill at the next open with T+1 settlement and modeled tax; backtests
use same-day close and are pre-tax. The historical research notes below are not
a fresh validation of the current deployment or a guarantee of future returns.

A self-contained paper-trading research harness. It fetches real Indian market
data, runs a **momentum stock strategy blended with an adaptive diversifier
basket**, paper-trades **₹1,00,000 of virtual money** with realistic **Groww**
costs, validates itself with **walk-forward (no look-ahead)** and a
**survivorship-robust** check, gives a **daily buy/hold/sell/cash call**, and
runs itself every weekday via a scheduled task.

> ⚠️ **Educational research only — NOT investment advice.** No real orders are
> ever placed. The author is not a licensed adviser. Backtests overstate live
> results. Any real-money decision, and its risk, is entirely yours.

---

## The honest headline

**Trading forward, never seeing the future:**

| Test | Trader | Nifty | Sharpe | Max drawdown |
|---|---|---|---|---|
| Walk-forward, 500 stocks (OOS) | **+130%** | +18% | ~1.6 | −13% |
| **Nifty-100, survivorship-robust (OOS)** | **+57%** | +17% | **1.29** | shallow |
| 3-year live paper book | **+61%** | +18% | — | **−15%** |

It **beats the Nifty in 4 of 5 years with no deep down years.** The large-cap,
survivorship-robust number (+57% vs +17%) is the one to trust.

## What we learned building it (the real value)

1. **Costs are lethal on a small book.** The naive first version *lost* money —
   1,000+ trades burned ~half the capital in Groww charges. Fix: trade rarely.
2. **Fast mean-reversion loses after costs; only momentum survives.** The system
   now does only trend/momentum.
3. **The one free lunch is combining *uncorrelated* things.** Adding a gold /
   silver / InvIT / cash basket (correlation to stocks ≈ 0) roughly **doubled the
   Sharpe and halved the drawdown.**
4. **Gold is insurance, not a return engine.** It had a *dead decade* (2013-18,
   +5% total) then rallied; recent gold gains are partly that rally. So it's
   *gated* (held only while trending) and *spread* into a basket, never over-bet.
5. **You can improve risk-adjusted return, not raw return.** Across every
   experiment (bigger universe, small-caps, adaptive allocation) raw return
   plateaued ~+130% OOS — that's the efficient market. What kept improving was
   Sharpe (0.8 → 1.6) and drawdown (−27% → −13%). **Diversifying trades some raw
   return for a lot of safety — you can't max both at once.**
6. **A small account's real edge is discipline, not secret signals** — running a
   validated, diversified, cost-aware system with a crash filter and not
   overriding it on emotion.

## The strategy (final)

- **Universe:** Nifty 500 (`data/nifty500.txt`); a 2,306-stock full-NSE list
  (`data/nse_all.txt`) is available but gave no extra return once liquidity is
  enforced.
- **Momentum engine:** 12-1 month return (skip last month) blended with 6-1,
  volatility-adjusted, only names above their 200-DMA; hold the top ~15,
  inverse-volatility sized, re-ranked quarterly.
- **Filters:** liquidity gate (~₹5cr/day median turnover — also a point-in-time
  size screen), max 4 per sector, Groww costs + 12bps slippage.
- **Diversifier basket** (`config.defensive_basket`): gold + silver + InvIT +
  cash, low-correlation to equities, rebalanced on the re-rank cadence.
- **Adaptive allocation** (`config.allocation`): the equity-vs-defensive split
  flexes with the market regime (≈45% equity in weak markets → 85% in strong);
  a diversifier is held only while *it* is trending up, else that slice sits in
  cash.
- **Crash filter:** no new stock buys when the Nifty is below its 200-DMA.

Everything is tunable in `config.json`.

## Usage

```bash
python scripts/daily_run.py            # refresh data, update the book, write call + dashboard
python scripts/show_call.py            # print today's call in plain text
python scripts/news_overlay.py         # LIVE news check on today's names (unvalidated overlay)
python -m qlab.engine                  # 5y system backtest vs Nifty
python -m qlab.optimize                # walk-forward (out-of-sample) validation
python scripts/validate.py             # full trust suite → runs/validation.json (dashboard reads it)
python scripts/validate_universe.py data/nse_all.txt   # test on the full NSE universe
python scripts/reset_book.py --yes     # start the paper book over
```

Open `reports/dashboard.html` after any run. **Automation:** a Windows Task
Scheduler job ("QuantLab Daily Momentum") runs `scripts/daily_run.bat` every
weekday at 18:30 IST — it refreshes data and rewrites the dashboard +
`runs/todays_call.json`. To see the call: open the dashboard, or run
`python scripts/show_call.py`. (Your PC must be on at that time; the run is
idempotent.)

## Architecture

```
config.json          all knobs (capital, universe, momentum, filters, basket, allocation, regime, costs)
qlab/
  data.py            Yahoo daily bars via urllib + cache; clean_ohlc drops corrupt ticks
  indicators.py      SMA/EMA/RSI/MACD/Bollinger/ATR/ADX/ROC + adjusted OHLC
  costs.py           Groww cost model (brokerage+STT+exch+SEBI+stamp+GST+DP)
  strategies.py      (legacy sleeves; momentum is the live engine)
  engine.py          one step_day() for backtest AND live; momentum ranking, basket rebalance,
                     adaptive allocation, gated diversifiers, no look-ahead
  metrics.py         CAGR/Sharpe/Sortino/maxDD/profit-factor/expectancy
  optimize.py        walk-forward optimization (train→OOS→roll)
  learn.py           per-trade post-mortems + adaptive strategy weights
  advisor.py         todays_call(): buy/hold/sell/cash with sizes, stops, win/loss scenarios
  news.py            LIVE Google-News overlay + crude risk/earnings flag (unvalidated)
  report.py          simple, insight-first HTML dashboard
  orchestrator.py    the daily loop
scripts/             daily_run(.py/.bat), show_call, news_overlay, validate, validate_universe, reset_book
data/                cached prices + universe/name/industry lists
runs/                state.json, journal.jsonl, todays_call.json, validation.json, weights.json
reports/dashboard.html
```

## Honest limits

- **Survivorship** isn't fully removed on the 500/2306 lists (they're *today's*
  listed stocks; fully-delisted failures are absent). The Nifty-100 check is the
  trustworthy read because large caps rarely vanish.
- **Small-cap slippage** is optimistic; the ₹5cr liquidity gate keeps fills
  realistic, and going smaller did not help.
- **Rebalance-timing luck** (~±15% on a single path); tranching would reduce it.
- **Fundamentals & news can't be backtested** with free data (no point-in-time
  history → look-ahead). `news.py` is a *live-only* review tool, never trusted
  blindly.
- **This is not a money-printer.** It's a disciplined, diversified system that
  beats the index on a risk-adjusted basis. That's the honest, achievable goal.

## Costs (Groww, approximate as of 2026)

`config.json → costs`. Delivery round-trip on a ₹6,000 order ≈ ₹46 (0.77%),
dominated by the DP charge + STT + per-order brokerage. **Verify against Groww's
live calculator and update** — these change with regulation.
# Current hardening status (September24, 2026)

Public paper app: https://dhruva-andy7204.streamlit.app/ . Canonical daily command:
`python -m dhruva.run_daily`. See [audit history](docs/AUDIT_HISTORY.md),
[pipeline](docs/DAILY_PIPELINE.md) and [progress](docs/HARDENING_PROGRESS.md).
The existing app is being repaired in place; original archive and ledger evidence
are retained. Recovery is labelled reconstruction. Tax/settlement repairs remain
pending; old descriptive claims below are subject to the audit, not certification.
