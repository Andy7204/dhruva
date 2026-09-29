# AGENTS.md — Dhruva v2

## What this is

Paper-only forward test of deterministic index strategies. Educational research,
not investment advice. Never add real order placement.

## Layout

```
lab/engine.py         backtest/replay engine: one-session lag, ETF costs, Indian FIFO tax, liquidation value
lab/strategies.py     24 pre-registered candidates (research) incl. the three live books
research/v2/          strategy search: fetch_indices.py, run.py, robustness.py, results/, README.md
data/indices/         official NSE Total Return Index history + GOLDBEES + Nasdaq-100 in INR (append-only)
data/trading_calendar.json   explicit NSE sessions/holidays; extend from official circulars only
config.v2.json        forward start, capital, the books, success criteria
dhruva/daily.py       guarded daily run: marketdata.update, forward.replay/record, digest
dhruva/forward.py     replays books; appends runs/forward/log.jsonl once per book per session
dhruva/performance.py forward metrics and pre-registered verdict
dhruva/watchdog.py    independent freshness check; dhruva/alerts.py opens/closes GitHub issues
dhruva/digest.py      change-only / Friday notices on a standing GitHub issue
streamlit_app.py      read-only public app
```

## Rules

1. Decisions are deterministic and use data up to the decision close; fills are
   at the next close. US-traded series (Nasdaq-100, world gold) are used from the
   next Indian date.
2. `runs/forward/log.jsonl` is append-only. A replay that disagrees with a saved
   row is reported as a warning, never rewritten.
3. `data/indices/*.csv` rows are never overwritten by updates; vendor revisions
   are reported.
4. Factor-index history before launch is NSE back-calculation; say so whenever
   quoting backtests.
5. Do not change books or criteria without the owner's request; log changes in
   `docs/SUCCESS_CRITERIA.md` and README.

## Debug

- Daily failed with "Data not yet published": NSE or Yahoo had not posted the
  session yet; the next scheduled run catches up (replay covers missed days,
  labelled `reconstructed`).
- NSE endpoint errors: niftyindices.com `BackPage/getTotalReturnIndexString`
  changed; inspect the site's historical data page network calls.
- Calendar expired: add official NSE holidays/special sessions to
  `data/trading_calendar.json`.
