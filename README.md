# Dhruva — index strategy paper lab

A public, paper-only forward test of three deterministic index strategies against
simply holding Nifty 50. Educational research, not investment advice. It places
no real orders.

Public app: https://dhruva-andy7204.streamlit.app/

## Why v2

The original stock-picking strategy (v1) lost to buying and holding Nifty over
2009–2026 once its data errors and backtest bias were fixed, so it was removed on
September29, 2026. Its final state is kept in Git under the tag `v1-final`.

v2 searched 24 standard index strategies on official NSE Total Return Index
history (point-in-time, dividends included, no survivorship bias), with ETF
costs, Indian capital-gains tax and liquidation value. See
[research/v2/README.md](research/v2/README.md) for the method, results and limits.

## The paper books (from the September30, 2026 close, INR10 lakh each)

| Book | Rule | Backtest after tax, 2007–2026 |
|---|---|---|
| A | 70% Nifty Midcap150 Momentum 50 + 30% gold, rebalanced yearly | about 17.5% a year, stable across review dates |
| B | 60% Nifty200 Momentum 30 + 20% gold + 20% Nasdaq-100 (INR), yearly | about 15.2% a year, stable across review dates |
| C | Monthly: hold the best of Momentum 30, Midcap Momentum 50, Nasdaq-100 and gold by average 1/3/6-month return, or a liquid fund if all are negative | 13.4–18.8% a year depending only on review timing: fragile |
| Nifty 50 | Buy and hold, same costs and tax | about 8.6% a year |

Backtests are not forecasts. Factor-index history before each launch date is
NSE's back-calculation; only 4–14 years are genuinely live. The pre-registered
pass/fail test is in [docs/SUCCESS_CRITERIA.md](docs/SUCCESS_CRITERIA.md).

## How it runs

- `.github/workflows/daily.yml` (weekdays 18:30 IST, often delayed by GitHub):
  `python -m dhruva.daily` checks the exchange calendar, appends the completed
  session's official NSE index levels, GOLDBEES and Nasdaq-100 in INR to
  `data/indices/`, replays every book with `lab/engine.py`, appends one row per
  book to `runs/forward/log.jsonl` (never rewritten) and commits.
- A notice is posted to a GitHub issue only when a book decides a new
  allocation, plus a Friday summary.
- `.github/workflows/watchdog.yml` checks freshness daily and opens a GitHub
  issue on failure.
- `streamlit_app.py` only reads saved files.

## Local use

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
.\.venv\Scripts\python.exe research\v2\run.py      # rerun the strategy search
```

## Maintenance

- `data/trading_calendar.json` is an explicit NSE holiday list. Add official
  dates (including special sessions such as Muhurat trading with their official
  timing) before it expires; the watchdog warns 14 days ahead.
- If niftyindices.com or Yahoo change their endpoints, `dhruva/marketdata.py`
  fails loudly rather than guessing.
