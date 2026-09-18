# AGENTS.md — Dhruva handoff for AI agents

You are an AI agent (e.g. ChatGPT with GitHub + Streamlit connectors) asked to run,
deploy, or debug **Dhruva**. Read this fully first. It is the source of truth for
the project's shape and the exact next steps.

> **What this is:** a Python **paper-trading research system** for Indian equities.
> It runs a diversified **momentum** strategy (top-N Nifty-500 stocks by 12-month
> momentum) blended with a defensive **basket** (gold/silver/InvIT/cash ETFs), with
> Groww transaction costs, Indian capital-gains tax, a realistic order lifecycle
> (next-open fills, T+1 settlement), a circuit-breaker, and a two-tier dashboard.
> **EDUCATIONAL / PAPER-TRADING ONLY — it places no real orders and gives no
> investment advice.** Never change it to place real orders or dispense advice.

## Golden rules
1. **Trading decisions stay deterministic.** Do NOT wire an LLM into buy/sell
   decisions. Gen-AI is used only to *explain* (see `qlab/narrator.py`).
2. **Never introduce look-ahead.** Signals use only past data (see `_facts`/momentum
   `shift`). Live fills are next-open; backtest fills are same-day close (documented).
3. **Keep it honest.** Model costs + tax; don't hide drawdowns; flag survivorship
   and other caveats. If a change makes returns look better, prove it's not a bug.

## Quickstart (local)
```bash
pip install pandas numpy streamlit         # Python 3.12+
python scripts/daily_run.py                # fetch latest, advance the live book, rebuild dashboard
python scripts/show_call.py                # today's plain-text call
streamlit run streamlit_app.py             # serve the dashboard at :8501
python -m qlab.engine                      # 5y backtest vs Nifty (sanity)
python scripts/validate.py                 # trust suite -> runs/validation.json
python scripts/compare3.py                 # 3-strategy backtest -> runs/backtest_comparison.json
```
Docker: `docker build -t dhruva . && docker run -p 8501:8501 dhruva`.

## Repo map
```
config.json            ALL knobs (universe, momentum, allocation, costs, tax, risk, books, settlement)
qlab/
  data.py              Yahoo daily bars via urllib (+ cache in data/cache/, clean_ohlc)
  indicators.py        technical indicators + adjusted OHLC
  engine.py            THE BRAIN (momentum rank, allocation, regime) + BACKTEST step_day (close-fill)
  livebook.py          LIVE order-management engine (next-open fill, T+1 settle, circuit-breaker, tax-aware exits)
  costs.py             Groww charges;  tax.py  capital-gains tax;  metrics.py  Sharpe/Sortino/CAGR/DD
  optimize.py          walk-forward validation
  advisor.py           today's call;  news.py  live news overlay (UNVALIDATED);  narrator.py  plain-English explainer (LLM optional)
  notify.py            Telegram sender;  report.py  two-tier HTML dashboard;  orchestrator.py  daily_run
scripts/               daily_run, show_call, news_overlay, validate, compare3, bakeoff, validate_universe, reset_book
runs/                  STATE: livebook_*.json, alert.txt, narrative.txt, validation.json, backtest_comparison.json
reports/dashboard.html the generated dashboard (Streamlit embeds this)
data/                  cache/ (prices), nifty500.txt, nse_all.txt, name/industry maps
streamlit_app.py       public app;  Dockerfile;  .github/workflows/daily.yml  cron;  DEPLOY.md
```

## The daily flow (`orchestrator.daily_run`)
load config -> fetch+clean data -> `engine.build_panel` (indicators+momentum) -> for each book in
`config.books`: `livebook.step` per unprocessed day (fill yesterday's scheduled orders at today's
open, settle T+1, run circuit-breaker, decide on the quarterly cadence, schedule new orders) ->
write `runs/livebook_<book>.json` -> `narrator.narrate` -> `report.build_multi_dashboard` ->
`runs/alert.txt` -> `notify.send_telegram`. Idempotent per day (safe to re-run).

## Deploy = autonomous public dashboard (do this)
Target: free public link that self-updates every weekday evening. Steps (see DEPLOY.md for detail):
1. **GitHub**: create a PUBLIC repo with THIS folder as the repo ROOT (don't nest it under a path
   with a space). Commit everything incl. `runs/backtest_comparison.json`, `runs/validation.json`,
   `reports/dashboard.html`, and ideally `data/cache/` (so the first cron run is fast).
2. **GitHub Actions**: the workflow `.github/workflows/daily.yml` already schedules the daily update
   (13:00 UTC / 18:30 IST, Mon–Fri) and commits the refreshed dashboard. Enable it in the Actions tab;
   test with "Run workflow".
3. **Streamlit Community Cloud** (share.streamlit.io): New app -> this repo -> main file `streamlit_app.py`
   -> Deploy. It auto-redeploys on each daily commit, so the public link stays fresh.
4. **Telegram alerts** (optional): @BotFather -> bot token; get chat id; add repo Secrets
   `TELEGRAM_TOKEN` + `TELEGRAM_CHAT`. **LLM narrator** (optional): add secret `ANTHROPIC_API_KEY`
   (or `OPENAI_API_KEY`) and the workflow env, else a rule-based narrator runs (no key needed).

## Debug playbook (known failure modes + fixes)
- **Windows console `UnicodeEncodeError` on `₹`**: cp1252 console. Import `qlab` first (it forces
  UTF-8 stdout) or set `PYTHONUTF8=1`. Data/dashboard are always UTF-8.
- **Regime shows a wrong 200-DMA / everything flips RISK-ON wrongly**: the benchmark cache got
  overwritten with MONTHLY data. Cause: fetching `^NSEI`/`GOLDBEES` with `rng="max"` returns monthly.
  Fix: `python -c "from qlab import data as D; D.get_history('^NSEI', rng='5y', refresh=True)"` (and any
  affected ETF). Never refetch live-used tickers at `rng="max"`.
- **A ticker 404s** (delisted/renamed, e.g. after a demerger): harmless; `get_universe` skips it. Replace in
  `data/nifty500.txt` if it matters.
- **`fetch failed` for many tickers**: rate-limit / network. Retry; increase pauses in `get_universe`.
- **Backtest looks too good (e.g. huge win rate)**: suspect a bug (historically: raw vs adjusted OHLC
  in stops, or the gated diversifier never selling). Verify against a large-cap survivorship-robust run.
- **Live book holds a diversifier it should have dropped**: the gate only sells on the rebalance
  cadence (`rebalance.long_term_rerank_days`), by design (low turnover).
- **Streamlit shows a stale page**: it redeploys on the repo commit; check the Actions run succeeded and
  committed `reports/dashboard.html`.

## Honest limitations (do not paper over these)
Survivorship bias (uses today's Nifty-500 list); backtest is pre-tax and same-day-close (mildly
optimistic vs the live book); small-cap slippage optimistic; momentum is streaky (beats the index
only ~2 of 5 years but wins big overall). News/fundamentals are NOT backtestable with free data.

## Suggested next steps for you, the agent
1. Deploy per the steps above; confirm the public Streamlit link updates after a manual "Run workflow".
2. Add Telegram + (optionally) the LLM narrator secrets.
3. If asked to improve: implement dividend-tax-at-slab, make the backtest next-open for consistency, or
   add the daily narrator via LLM — all WITHOUT touching the deterministic decision core.
4. Keep `README.md` (human overview) and this file (agent overview) in sync with any change.

## Deployment implementation
The daily workflow supports manual dispatch and weekdays at 13:00 UTC, requests
`contents: write`, serializes runs, and commits `runs/`, `reports/dashboard.html`,
and `data/cache/`. It passes optional `TELEGRAM_TOKEN`, `TELEGRAM_CHAT`,
`ANTHROPIC_API_KEY`, and `OPENAI_API_KEY` repository secrets to the daily process.
No narrator key is required; Anthropic is the LLM option without an OpenAI key.

## Isolated strategy challenge study
`research/README.md` and `research/PROTOCOL.md` describe the reproducible challenge
tests; `research/results/REPORT.html` contains the full report. These scripts read
cached data and write only under `research/`. They do not alter production logic,
state or dashboards. The baseline is current policy with audited research
execution (past-only cleaning, adjusted ATR, gap stops, settled cash, FIFO,
shared tax reserve and actual 70/30 books), not an exact deployed-engine replay.
Current constituent lists, adjusted prices and simplified constant tax rates
remain material limitations. No variant was chosen for deployment.

## Hardening mission and audit
Read `docs/HARDENING_MISSION.md` and `docs/HARDENING_PROGRESS.md` for the ordered
hardening work. `docs/CURRENT_STATE_AUDIT.md` supersedes optimistic implementation
claims above: current live NAV does not reserve tax, T+1 does not restrict cash,
missed sessions are skipped, and stale data can look healthy. Phase 0 probes
reproduce these defects without altering production. Preserve v1 before fixes;
decision/accounting changes need a new prospective version. Never backdate evidence.

The original is frozen in `strategies/dhruva_v1/strategy_manifest.yaml` and
`snapshot/`. `python -m dhruva.freeze` verifies hashes; `daily_run` rejects changed
v1 economic source/config/universe before fetching or writing. Never regenerate
the frozen archive to accept a code change. Corrections use a new prospective track.

The v1 daily wrapper now captures per-symbol evaluations and both book states in
`runs/ledger/dhruva_v1/` before updating book projections. Input snapshots and
event segments are immutable through the API, hash-checked and Git-persisted.
Legacy observations are labelled, not backdated. See `docs/LEDGER.md`.
`runs/ledger/acceptance_test_only/` is synthetic and must never enter performance.

The daily CLI uses an operational guard (`dhruva.operations`): before 16:30 IST
or on known non-trading days it records `SKIPPED_NOT_DUE` without advancing v1.
Calendar coverage is explicit in `data/trading_calendar.json`; expired coverage
fails closed. Operational completion does not certify data quality. Dependencies
are pinned in `requirements.lock`; workflow outcomes persist under `runs/operations`.

`streamlit_app.py` now reads `dhruva.health` every 60 seconds during an active
session. It renders one recorded NAV (before tax), rejects partial/corrupt book
totals, and flags stale, unfinished or failed evidence. It no longer embeds the
legacy HTML with conflicting totals/unsupported claims; that file is preserved.
V1 must never appear HEALTHY while its audited economic defects remain.
