You are taking over an existing project called **Dhruva**, an AI-assisted systematic investing / market research system focused primarily on Indian equities.

Dhruva already has:
- historical backtesting
- an existing strategy/system that has now entered live forward/shadow testing
- a Streamlit deployment
- GitHub repository
- GitHub Actions / cron intended to update the system daily
- relatively low-frequency strategies, where trades or portfolio changes may happen only occasionally
- a next meaningful rebalance/update potentially ~63 days away

A lot of Dhruva has been built using Claude/AI coding agents.

Your job is NOT to make Dhruva look sophisticated.

Your job is to make Dhruva:

**credible, reproducible, auditable, reliable, autonomous, modular, and genuinely useful.**

The end-state should conceptually be:

**market data**
→ validation
→ research
→ signal generation
→ portfolio construction
→ live shadow ledger
→ performance tracking
→ continual monitoring
→ alerts
→ Streamlit dashboard
→ eventually execution / monetization infrastructure

The current priority is NOT monetization.

The current priority is:

**build trustworthy infrastructure + preserve the live experiment + accumulate genuine forward evidence.**

---

# CORE RULE: COMPLETE EACH PHASE BEFORE MOVING TO THE NEXT

Work sequentially.

Do NOT simultaneously create half-finished implementations across many areas.

For each phase:

1. inspect current implementation
2. identify gaps
3. implement required changes
4. add tests
5. run tests
6. verify actual behavior
7. document what changed
8. satisfy the phase acceptance criteria
9. commit/save the state
10. only then proceed to the next phase

If something cannot be completed, document exactly why and what remains blocked.

Do NOT mark something "done" because code exists.

A capability is only DONE if:

**implemented + tested + demonstrated working.**

---

# PHASE 0 — FULL CURRENT-STATE AUDIT

DO THIS FIRST.

Do not modify architecture substantially before understanding what already exists.

Inspect the entire repository.

Create:

`docs/CURRENT_STATE_AUDIT.md`

Audit whether Dhruva genuinely demonstrates:

- Python engineering
- market-data ingestion
- data engineering
- quantitative finance
- statistics
- time-series processing
- backtesting
- portfolio construction
- risk management
- APIs
- machine learning
- AI/LLM usage
- agents
- research orchestration
- GitHub Actions
- cron scheduling
- Streamlit deployment
- persistent storage
- monitoring
- logging
- testing
- live performance tracking
- reproducibility
- product/dashboard UX

For every capability classify it as:

- ✅ implemented and genuinely working
- 🟡 partially working / fragile
- ❌ absent
- 🗑 unnecessary / misleading / overengineered

For each capability document:

1. files/modules involved
2. what it actually does
3. evidence it works
4. known weaknesses
5. whether it provides real value
6. action:
   - KEEP
   - FIX
   - BUILD
   - DELETE
   - DEFER

Do NOT add technologies just for resume value.

If ML is unnecessary, do not use ML.

If an API adds no architectural value, don't add one.

If agents make a deterministic process worse, don't use agents there.

---

## PHASE 0 DELIVERABLES

Produce:

- `docs/CURRENT_STATE_AUDIT.md`
- capability/gap matrix
- architecture diagram of CURRENT Dhruva
- list of dangerous issues
- list of unnecessary components
- list of missing critical components
- recommended execution plan based on actual repository state

---

## PHASE 0 ACCEPTANCE GATE

Before Phase 1:

You must be able to explain clearly:

- how data currently enters Dhruva
- how signals are produced
- how portfolios are generated
- how backtests work
- where state is stored
- how GitHub Actions update data
- how Streamlit gets fresh data
- whether daily automation is genuinely working
- where live results currently live
- what can silently fail

Only then continue.

---

# PHASE 1 — FREEZE AND PROTECT THE LIVE EXPERIMENT

This is the most important phase.

The currently live strategy must become a frozen version:

`Dhruva v1.0`

Its historical/live behavior must NEVER silently change because code changes later.

Create:

`strategies/dhruva_v1/strategy_manifest.yaml`

and:

`strategies/dhruva_v1/README.md`

Record:

- strategy version
- Git commit hash
- live start date
- universe
- benchmark
- factor definitions
- factor weights
- signal rules
- ranking logic
- entry rules
- exit rules
- rebalancing rules
- portfolio constraints
- risk rules
- transaction-cost assumptions
- slippage assumptions
- starting NAV/capital
- data sources
- backtest period
- known limitations

If strategy logic changes later:

DO NOT overwrite v1.0.

Create:

`v1.1`

or:

`v2.0`

depending on severity.

A strategy logic change should create a new forward track.

Infrastructure-only changes may retain the same strategy version if they do not alter decisions.

Document all such decisions.

---

# PHASE 2 — BUILD THE IMMUTABLE LIVE SHADOW LEDGER

Dhruva needs a permanent record proving:

> "This is what the system decided at this time before the future was known."

Create an append-only live ledger.

Record every evaluation and decision.

At minimum:

- run_id
- generated_at
- data_cutoff_at
- effective_date
- strategy_id
- strategy_version
- Git commit
- configuration hash
- data snapshot/version
- ticker
- company name
- action
- previous weight
- target weight
- signal score
- signal components
- market price
- rationale
- portfolio NAV
- benchmark level
- execution mode
- execution status

Support actions such as:

- BUY
- SELL
- HOLD
- INCREASE
- REDUCE
- NO_ACTION

Original records must NEVER be modified.

Corrections must be new append-only events.

Later realized results may be associated with the original event but must not overwrite original input/state.

Use the simplest reliable persistent storage appropriate to the architecture.

Do not introduce heavy infrastructure unnecessarily.

---

## LEDGER MUST SURVIVE

- Streamlit restart
- GitHub runner destruction
- deployment rebuild
- dependency reinstall
- machine restart

Do NOT store the only copy of live history on ephemeral storage.

---

## PHASE 2 ACCEPTANCE TEST

Demonstrate:

1. generate test signal
2. record it
3. restart/redeploy
4. confirm it remains
5. rerun same pipeline
6. ensure duplicate signal is NOT created
7. attempt mutation
8. confirm original record cannot silently change

Only then proceed.

---

# PHASE 3 — AUDIT GITHUB ACTIONS + CRON + STREAMLIT

Dhruva already claims daily autonomous operation.

Prove it.

Do NOT assume the automation works because YAML exists.

Inspect:

`.github/workflows/`

Verify:

- cron timing
- timezone assumptions
- trading days
- weekends
- holidays
- default branch behavior
- workflow permissions
- secrets
- environment variables
- API keys
- Python version
- dependency installation
- package locking
- caching
- concurrency
- retries
- timeouts
- failure handling

Where possible inspect historical GitHub Actions runs.

Look for:

- failed runs
- skipped runs
- flaky runs
- cancelled runs
- long-running jobs
- stale artifacts
- pipelines that completed but failed to refresh data

---

# PHASE 4 — VERIFY STREAMLIT PRODUCTION BEHAVIOR

Audit the deployed Streamlit app.

Determine:

- hosting provider
- branch tracked
- deployment trigger
- deployment health
- secrets management
- cache behavior
- persistence behavior
- dependency reproducibility
- startup behavior
- stale-data behavior

Critical rule:

**Streamlit must never look healthy when backend data is stale.**

Display prominently:

- last successful pipeline run
- latest market-data date
- current strategy version
- current Git commit
- system health
- data freshness

For example:

`Last successful update: 2026-09-17 07:14 IST`

`Latest market data: 2026-09-16`

`Strategy: Dhruva Momentum v1.0`

`Commit: abc123`

`System status: HEALTHY`

If stale:

`WARNING — DATA STALE`

Do NOT silently show yesterday's data.

---

## PHASE 3–4 ACCEPTANCE GATE

Demonstrate:

- scheduled workflow executes
- pipeline actually refreshes data
- Streamlit receives latest output
- stale data is detected
- failed backend update does not appear as healthy
- required secrets are present
- restart does not destroy live records

Only then continue.

---

# PHASE 5 — CREATE ONE CANONICAL DAILY PIPELINE

Dhruva must have ONE primary entrypoint.

For example:

`python -m dhruva.run_daily`

GitHub Actions should call this.

Avoid duplicating business logic in YAML.

Pipeline:

**fetch data**
→ validate
→ clean
→ transform
→ compute signals
→ construct portfolio
→ compare with previous state
→ write ledger
→ update live NAV
→ update benchmark
→ run risk checks
→ generate report
→ write heartbeat
→ send alerts if necessary

If nothing changed:

return:

`NO ACTION — strategy unchanged`

Do NOT manufacture activity.

---

# PHASE 6 — DATA ENGINEERING + POINT-IN-TIME SAFETY

Now audit historical correctness.

Check for:

- look-ahead bias
- survivorship bias
- future index membership
- delisted stocks
- revised fundamentals
- corporate actions
- splits
- dividends
- missing OHLCV
- stale data
- transaction costs
- slippage
- liquidity assumptions
- universe-selection bias

Separate:

`raw`

→ `validated`

→ `transformed`

→ `features`

Data should be versioned/cacheable where useful.

Every signal should know which data snapshot generated it.

Add validation for:

- duplicate rows
- impossible prices
- missing prices
- zero volume
- stale timestamps
- suspicious jumps
- incorrect corporate-action adjustments
- missing universe members

---

## CRITICAL RULE

The system must distinguish:

`NO SIGNAL`

from:

`FAILED TO GENERATE SIGNAL`

from:

`PIPELINE NEVER RAN`

from:

`DATA WAS STALE`

These must never be treated as equivalent.

---

# PHASE 7 — UNATTENDED OPERATION

Dhruva should run for weeks without me checking GitHub manually.

Create structured health records.

Every run records:

- run_id
- start time
- end time
- status
- Git commit
- strategy version
- data status
- latest market-data timestamp
- portfolio-engine status
- risk-engine status
- ledger status
- benchmark status
- report status
- warnings
- fatal errors

Possible statuses:

- SUCCESS
- SUCCESS_NO_ACTION
- DEGRADED
- FAILED

---

# PHASE 8 — HEARTBEAT + WATCHDOG

A failed cron cannot report its own failure if it never runs.

Therefore create the simplest reliable independent watchdog.

Watchdog should verify:

- expected daily run occurred
- latest successful run is recent
- market data is fresh
- ledger heartbeat exists

If main pipeline misses expected runs:

alert.

Do not build distributed-systems theatre.

Simple and robust wins.

---

# PHASE 9 — ALERTING

Implement ONE reliable external alert channel.

Examples:

- email
- Telegram
- Slack
- Discord
- automatic GitHub Issue

Choose the easiest reliable option.

Alert when:

- scheduled run fails
- scheduled run is missed
- data becomes stale
- ledger write fails
- strategy calculation fails
- benchmark update fails
- risk limits break
- portfolio changes unexpectedly
- deployment becomes unhealthy

Do NOT spam daily success notifications unless configured.

---

# PHASE 10 — TEST FAILURE AND RECOVERY

Actively simulate failures.

Examples:

- data API unavailable
- malformed response
- incomplete data
- duplicate daily run
- GitHub job terminates halfway
- Streamlit restarts
- database temporarily unavailable
- stale cache
- one daily run fails
- next daily run starts
- corrupted intermediate file
- benchmark unavailable

System should recover safely.

Daily pipeline should be idempotent where appropriate.

Running it twice should not duplicate ledger events or trades.

---

## PHASE 10 ACCEPTANCE GATE

Prove:

- duplicate run safe
- stale data blocks misleading signal generation
- failed pipeline alerts
- recovery works
- ledger persists
- missed heartbeat is detected

Only then treat Dhruva as genuinely autonomous.

---

# PHASE 11 — AUDIT AND HARDEN BACKTESTING

Only after live infrastructure is protected, audit backtesting.

Track:

- total return
- CAGR
- benchmark return
- excess return
- volatility
- Sharpe
- Sortino
- maximum drawdown
- Calmar
- turnover
- hit rate
- average winner
- average loser
- trade count
- average holding period
- market exposure
- rolling returns
- rolling drawdowns
- transaction costs

Where useful:

- bull-market capture
- bear-market capture
- rolling alpha
- sector exposure
- factor exposure

Use:

- train/validation/test where applicable
- walk-forward testing
- multiple market regimes
- sensitivity analysis

Do NOT optimize parameters until the curve looks pretty.

---

# PHASE 12 — STRICT BACKTEST VS LIVE SEPARATION

Create two completely separate concepts:

## BACKTEST PERFORMANCE

Historical simulation.

## LIVE FORWARD PERFORMANCE

Only decisions timestamped after live start date.

Never mix the two.

Create a live NAV indexed from:

`100`

Track against appropriate benchmarks.

Potential benchmarks:

- Nifty 50
- Nifty 500
- relevant momentum index
- relevant factor index

Do not select benchmarks after seeing which one Dhruva beats.

---

# PHASE 13 — PORTFOLIO CONSTRUCTION ENGINE

Dhruva must produce more than stock scores.

It should answer:

> "What portfolio should exist right now?"

Define:

- position size
- max stock weight
- sector exposure
- concentration limits
- liquidity requirements
- turnover constraints
- cash allocation
- diversification
- rebalance threshold
- exit logic
- minimum hold period if relevant
- risk limits

Output:

**current portfolio**

and:

**changes from previous portfolio**

---

# PHASE 14 — BUILD A PROPER STRATEGY INTERFACE

Do not hard-code everything into one monster pipeline.

Create a shared interface conceptually like:

`Strategy`

with:

- `get_universe()`
- `compute_signals()`
- `rank_assets()`
- `construct_portfolio()`
- `check_exit_conditions()`
- `rebalance_due()`
- `explain_decision()`

Shared infrastructure:

- data
- ledger
- portfolio engine
- risk
- analytics
- reports
- monitoring

Strategies keep their own:

- logic
- history
- version
- benchmark
- track record

---

# PHASE 15 — CURRENT STRATEGIES FIRST, FUTURE PRODUCTS LATER

Dhruva may eventually contain:

## Dhruva Momentum

Systematic momentum / relative-strength portfolio.

## Dhruva Long-Term Compounders

Lower-turnover quality/fundamental/growth investing.

## Dhruva Tactical

Regime-aware tactical strategy.

Do NOT invent these solely because they sound productizable.

First identify what genuinely exists today.

Only create new strategy families if they have a clear investment hypothesis and independent evaluation.

---

# PHASE 16 — RESEARCH ORCHESTRATOR

Now enhance research.

Important:

Do not copy US-centric architecture blindly.

For Indian equities prioritize:

### Fundamentals

- NSE filings
- BSE filings
- quarterly results
- annual reports
- concall transcripts
- management commentary
- shareholding patterns
- promoter holdings
- promoter pledging
- corporate actions
- bulk/block deals
- institutional ownership where reliable

### Market / positioning

Where available:

- FII/DII flows
- futures open interest
- options open interest
- put-call indicators
- futures basis
- volatility
- delivery volume
- liquidity
- breadth

### Technical

- momentum
- relative strength
- trend
- volatility
- drawdown
- breadth
- volume
- liquidity
- regime indicators

### News / events

- earnings
- management changes
- regulatory action
- litigation
- corporate actions
- acquisitions
- sector developments
- material company events

Every research item should preserve:

- source
- publication time
- retrieval time
- reference/URL
- relevant company/ticker

---

# PHASE 17 — AI / AGENT LAYER

Use agents where they genuinely improve Dhruva.

Possible roles:

## Filing Analyst

Summarizes new company filings.

## Earnings Analyst

Extracts:

- growth changes
- margin changes
- guidance
- risks
- management commentary

## News Analyst

Deduplicates and summarizes important events.

## Bear Analyst

Attempts to falsify the investment case.

## Portfolio Critic

Examines:

- concentration
- correlated bets
- hidden sector exposure
- risk clusters

## Report Writer

Converts deterministic outputs into readable reports.

Architecture should conceptually be:

**deterministic quant engine**

+

**research agents**

+

**portfolio/risk engine**

+

**explanation layer**

LLMs must not silently override deterministic rules.

If an AI opinion affects portfolio construction, that influence must be:

- explicit
- logged
- reproducible where possible
- measurable
- separately evaluated

---

# PHASE 18 — ML ONLY IF JUSTIFIED

Audit whether ML already exists.

If yes determine:

- target variable
- feature set
- validation method
- leakage risk
- out-of-sample improvement
- stability
- usefulness

Potential legitimate ML use:

- regime classification
- anomaly detection
- earnings/event classification
- risk forecasting
- ranking enhancement

If ML adds no measurable value:

DO NOT USE IT.

Simple robust factors > fancy ML for no reason.

---

# PHASE 19 — UX / STREAMLIT PRODUCT

Only now polish the UI.

Do not waste a week making gradients while the ledger is broken.

Create clear sections.

## HOME

Show:

- system health
- live strategy
- current portfolio
- live NAV
- benchmark NAV
- last successful update
- latest market-data date
- next rebalance/evaluation date
- latest decision
- risk status

## DECISIONS

Immutable chronological ledger.

## PORTFOLIO

- holdings
- weights
- sectors
- concentration
- P&L if appropriate

## PERFORMANCE

Clear separation:

**BACKTEST**

vs

**LIVE**

Include:

- returns
- benchmark comparison
- drawdowns
- rolling metrics
- turnover

## RESEARCH

For holdings:

- signals
- fundamentals
- filings
- news
- AI summaries
- sources

## METHODOLOGY

Explain what Dhruva does.

## SYSTEM HEALTH

Show:

- cron status
- latest pipeline
- data freshness
- current version
- current commit
- recent failures

Favor trust and clarity.

Do NOT create a cyberpunk Bloomberg cosplay terminal.

---

# PHASE 20 — TRUST LAYER

For every strategy create a Strategy Card.

Include:

- purpose
- universe
- benchmark
- live start date
- expected rebalance frequency
- expected turnover
- methodology
- risk profile
- known weaknesses
- backtest results
- live results
- current version
- version history

Maintain:

`CHANGELOG.md`

Example:

`v1.0 — original frozen live strategy`

`v1.1 — infrastructure fix only; strategy unchanged`

`v2.0 — changed ranking methodology; new live track started`

Never rewrite the past.

---

# PHASE 21 — API ONLY IF ARCHITECTURALLY USEFUL

If the system benefits from a proper backend boundary, implement something lightweight such as FastAPI.

Potential endpoints:

- `/health`
- `/strategies`
- `/portfolio/current`
- `/signals`
- `/performance`
- `/research/{ticker}`

Do this only if useful.

Do NOT add FastAPI because "API development" looks good on LinkedIn.

---

# PHASE 22 — EXECUTION ABSTRACTION

Eventually Dhruva may support:

research
→ portfolio
→ rebalance
→ execution

For now create abstraction only if architecture benefits.

Modes:

- SHADOW
- PAPER
- MANUAL_APPROVAL
- EXECUTED

Possible states:

- recommendation generated
- waiting for approval
- approved
- simulated
- executed
- failed

Do NOT enable autonomous real-money trading unless explicitly requested later.

---

# PHASE 23 — FUTURE PRODUCT ARCHITECTURE

Create:

`docs/FUTURE_PRODUCT_ARCHITECTURE.md`

Dhruva may eventually support:

- personal investment system
- public analytics
- registered research product
- B2B research infrastructure
- model portfolios
- strategy subscriptions

Possible intellectual products:

- Dhruva Momentum
- Dhruva Long-Term Compounders
- Dhruva Tactical

Architecture may eventually need:

- multi-user support
- multi-strategy support
- user portfolios
- notifications
- broker integrations
- subscriptions
- billing
- compliance records
- strategy marketplace

But:

DO NOT IMPLEMENT COMMERCIAL FEATURES YET.

Current priority:

**live evidence.**

---

# PHASE 24 — COMPLIANCE GATE

Create:

`docs/COMPLIANCE_GATES.md`

Do NOT assume that:

`not financial advice`

solves regulatory requirements.

Document what must be reviewed before:

- selling signals
- publishing recommendations
- offering model portfolios
- charging subscriptions
- executing for other users
- personalized recommendations
- brokerage integration

Do not make unsupported legal claims.

Just ensure architecture allows compliance controls later.

---

# PHASE 25 — CAREER / TECHNICAL CASE STUDY

Once the implementation is genuinely working create:

`docs/TECHNICAL_CASE_STUDY.md`

Explain:

## Problem

Systematic market research and portfolio monitoring.

## Architecture

End-to-end data flow.

## Python

What core engineering exists.

## Data Engineering

What is collected, validated and versioned.

## Quantitative Work

Signals, portfolio construction and backtesting.

## Statistics

Metrics and evaluation.

## AI

Where agents actually contribute.

## ML

Only if legitimately used.

## APIs

Only if legitimately used.

## Deployment

Streamlit + GitHub Actions.

## Automation

Scheduled daily pipeline.

## Monitoring

Heartbeat, stale-data detection, alerts.

## Reliability

Handling failures and bad data.

## Product Thinking

How architecture supports future strategy products.

Be honest about AI assistance.

Do NOT claim I manually coded everything.

Frame it as:

**AI-assisted engineering where I designed, directed, evaluated, tested and iterated the system using coding agents.**

---

# FINAL SYSTEM REQUIREMENT

Dhruva should eventually reach the point where I can ignore it for several days.

When I return, one of two things must be true:

### CASE 1

Everything worked.

### CASE 2

Dhruva already alerted me that something failed.

There must NOT be a third case:

> "System silently stopped updating six days ago but the Streamlit dashboard still looked fine."

---

# EXPECTED DAILY OUTPUT

Example healthy run:

```text
DHruva DAILY RUN
================

Run ID: 2026-09-17-001

SYSTEM
------
Environment: production
Git commit: abc123
Strategy: Dhruva Momentum v1.0

HEALTH
------
GitHub cron: PASS
Data ingestion: PASS
Data freshness: PASS
Portfolio engine: PASS
Risk engine: PASS
Ledger: PASS
Benchmark: PASS
Streamlit freshness: PASS

Latest market data: 2026-09-17
Last successful pipeline: 2026-09-17 07:14 IST

STRATEGY
--------
Rebalance due: NO
New signals: NONE
Portfolio changes: NONE

PERFORMANCE
-----------
Live NAV: 104.2
Benchmark NAV: 102.7

RESULT
------
NO ACTION — strategy unchanged.

Ledger updated.
Heartbeat updated.
Report generated.
```

Example failure:

```text
DHruva DAILY RUN
================

STATUS: FAILED

Failure:
Market data ingestion failed.

Last valid market data:
2026-09-16

IMPORTANT:
No strategy conclusion generated.

This run MUST NOT be interpreted as NO SIGNAL.

Ledger unchanged.
Failure heartbeat written.
Alert sent.
```

Example genuine new signal:

```text
NEW SIGNAL

Strategy:
Dhruva Momentum v1.0

Ticker:
XYZ

Action:
BUY

Previous weight:
0%

Target weight:
7.5%

Generated at:
[timestamp]

Data cutoff:
[timestamp]

Git commit:
[hash]

Signal evidence:
- momentum rank
- trend state
- liquidity
- portfolio constraints

Decision permanently stored as ledger event #123.
```

---

# FINAL PRODUCTION READINESS TEST

Create:

`docs/PRODUCTION_READINESS.md`

Verify with evidence:

- cron actually runs
- GitHub Actions work
- latest data arrives
- stale data detected
- failures raise alerts
- ledger is immutable
- ledger persists
- duplicate runs are safe
- current version recorded
- commit hash recorded
- Streamlit shows freshness
- Streamlit shows stale warning
- watchdog detects missed run
- pipeline recovers after failure
- no local machine needs to remain online
- live performance is separated from backtest
- new strategy versions cannot rewrite old records

Do not write:

`Implemented.`

Show evidence.

---

# FINAL WORKING RULE

For every proposed feature ask:

> Does this make Dhruva more reliable, reproducible, useful, credible, or measurably better?

If not:

**fuck it — don't build it.**

Do not maximize complexity.

Do not maximize AI.

Do not maximize ML.

Do not maximize number of dashboards.

Do not maximize lines of code.

Maximize:

**trustworthiness + reproducibility + automation + evidence.**

The strongest future Dhruva is not the one with the most technology.

It is the one where, after several years, we can say:

> Every decision was timestamped before the outcome was known, the system ran autonomously, failures were visible, methodology was versioned, and the full live track record still exists unchanged.

That is the asset we are building.

---

# EXECUTION BEHAVIOR

Do not stop after producing documentation.

Actually work through the phases.

At the end of EVERY phase, report:

### PHASE COMPLETED
What was changed.

### FILES CHANGED
Exact files.

### TESTS
What was tested.

### EVIDENCE
Proof it works.

### ISSUES FOUND
Any problems.

### DECISIONS
Anything intentionally deferred/deleted.

### NEXT PHASE
What you will implement next.

Then continue.

Do not ask me to manually approve every phase unless there is a genuinely irreversible or dangerous action.

Make reasonable engineering decisions autonomously.

Do not overwrite working history.

Do not fabricate results.

Do not fabricate successful tests.

Do not mark something complete unless you actually verified it.

If the repository contains flawed assumptions, challenge them rather than preserving them blindly.

The mission is:

**turn Dhruva from an AI-built side project into a credible long-running quantitative research system whose live evidence compounds over time.**