# Dhruva: complete operational handoff

Prepared September29, 2026, Asia/Kolkata. Assumes “Cloud Code” means **Claude Code**.
This file is a dated handoff, not a claim that future runs or deployment are healthy.
Use the companion [handoff checklist](HANDOFF_CHECKLIST.md) for next actions.

## 1. Where everything is

| Item | Location |
| --- | --- |
| Existing Windows working folder | `Z:\dhruva` |
| Public Git repository | https://github.com/Andy7204/dhruva |
| Branch / remote | `main` / `origin` pointing to the repository above |
| Public app | https://dhruva-andy7204.streamlit.app/ |
| Streamlit deployment management | https://share.streamlit.io/ — sign in with the deployment owner's account |
| App entry file, repository root | `streamlit_app.py` |
| Main settings | `config.json` |
| Python dependencies | `requirements.lock`; GitHub uses Python3.12.14 |
| Live books | `runs/livebook_balanced.json`, `runs/livebook_aggressive.json` |
| Immutable evidence | `runs/ledger/dhruva_v1/` |
| Price cache and universe | `data/cache/`, `data/nifty500.txt` and related maps |
| Historical generated report | `reports/dashboard.html` — not the current embedded public UI |
| Historical research | `research/results/REPORT.md`, `REPORT.html`; `research/PROTOCOL.md` |
| Consolidated audit | `docs/AUDIT_HISTORY.md` |
| Latest checkpoints | `docs/HARDENING_PROGRESS.md` — newest entries first |

If Claude Code is on this Windows computer, open the existing folder. On another
machine, clone the public repository; `Z:` is a local/mapped drive, not a portable
cloud path. Repository contents are already at its root; do not nest another dhruva
folder when deploying. No ChatGPT attachment is needed for routine operation.

## 2. What the user actually wants

A normal public app showing daily deterministic BUY/SELL/HOLD paper calls from
latest completed validated prices, understandable strategy, honest backtests and
a separate accumulating forward paper-performance history against Nifty.
Daily evaluation does **not** require daily trades: retain the63-session allocation
cadence. Stop changing strategy merely to manufacture activity or better returns.

Original audit work grew into26 phases and then10; the user cancelled mandatory
completion of both on September26. The focused release was accepted September28.
Later requests authorized selected important repairs and the explicit income
simulation. Old phase tables remain audit context, not an active obligation.
Do not revive unlimited hardening, architecture, research or token-consumption work.

## 3. Safety and history rules

- Paper only: no real broker orders or personalized investment advice.
- Buy/sell decisions stay deterministic. Optional AI only explains saved facts.
- No future prices or unfinished bars in signals; next-open live execution.
- Costs, modeled tax, losses and limitations must remain visible.
- Fix existing app/books in place; do not create a parallel “degraded” product.
- Original September17 fills were simulated, not real trades. Original observations,
  corrections and later forward observations are distinct.
- Never invent historical generation timestamps, distributions or exchange sessions.
- Preserve original Git/archive and ledger evidence. `python -m dhruva.freeze`
  verifies archive integrity, not equality between active code and original code.
- Never reset books to make a failure disappear. Recovery/corrections need explicit
  provenance; never overwrite immutable segments or erase original evidence.

## 4. Strategy in plain language

Initial paper capital is INR100,000: balanced core70,000 and aggressive satellite30,000.
The strategy ranks eligible stocks by trailing momentum, applies liquidity/sector
and sizing constraints, and blends stock exposure with a defensive basket that can
include gold/silver, an infrastructure trust, liquid ETF or cash. Current parameters
and per-book overrides live in `config.json`, not in this document.

Nifty's200-day trend filter limits new stock purchases. The defensive assets also
have trend gates. Both books share the market filter, so the split does not diversify
between buying weakness and buying strength. Decisions normally rebalance every63
trading sessions; stops and risk controls are evaluated daily. Circuit-breaker and
exit rules can act outside the normal cadence. Pending orders are not completed fills.

The design can miss sharp rebounds; it is not a bottom detector. The existing
challenge research examined such trade-offs; no research variant was promoted.
Do not say profitability is proved by an operationally successful daily job.

## 5. Current architecture and daily flow

`python -m dhruva.run_daily` is the canonical entry point. Old daily CLI delegates
to it. Operations guard checks the calendar and completed-session boundary, records
attempts/stages/errors, and serializes execution. Normal earliest boundary16:30IST;
normal scheduled publication18:30IST, subject to GitHub delays.

The pipeline fetches/caches data, excludes incomplete bars, validates freshness and
universe coverage, builds trailing features, and replays unprocessed sessions in
order. Missing held/benchmark data fail closed. Recovery is labelled reconstruction
at its real generation time. It does not pretend missed days were originally live.

`qlab.livebook` fills prior decisions at the next eligible quoted open, handles
delivery eligibility, cash settlement, gap stops and costs; decisions use the
existing engine. Adjusted data supplies signals, quoted OHLC supplies executable
units and valuation. Revised held raw history requires explicit reconciliation.

Shared taxpayer FIFO inventory and tax reserve reconcile the two virtual books.
Sale proceeds cannot fund same-open purchases. Orders have permanent IDs and retain
their history. The ledger captures state/input/event evidence before saved book
projections are published. Retries must not duplicate fills, income or dates.

The report and narrative are generated; the publisher safely commits `runs/`,
`reports/dashboard.html` and `data/cache/`. Failure evidence is also preserved.
The Streamlit app reads saved health/books/evidence, not freshly revalued quotes.
It refreshes checks during an active session. Full snapshot verification remains
in daily/watchdog paths; UI avoids decompressing all snapshots on each refresh.

| Module | Responsibility |
| --- | --- |
| `qlab/engine.py` | Deterministic strategy, legacy close-fill historical engine |
| `qlab/livebook.py`, `lots.py` | Paper execution, delivery/cash restrictions, FIFO |
| `qlab/tax.py`, `costs.py`, `accounting.py` | Shared reserve, charges, reconciliation |
| `qlab/income.py` | Evidenced cash/unit receipts; source hashes and credit eligibility |
| `qlab/income_model.py` | Separate assumption-only income estimate |
| `qlab/data.py`, `indicators.py` | Cached market data and trailing features |
| `qlab/orchestrator.py` | End-to-end book/evidence/report update |
| `dhruva/calendar.py`, `operations.py` | Session eligibility and operational state |
| `dhruva/health.py`, `presentation.py` | Verified saved status and read-only views |
| `dhruva/publication.py` | Safe publication under concurrent remote updates |
| `dhruva/watchdog.py`, `alerts.py` | Independent checks and external GitHub incidents |
| `qlab/narrator.py` | Rule prose or optional unverified AI wording; provenance |

## 6. What has been repaired

Detailed original findings and evidence are in `AUDIT_HISTORY.md` and
`ACCOUNTING_REPAIRS.md`. Principal completed repairs include:

- Chronological recovery instead of silently skipping missed sessions.
- Permanent order IDs/history instead of disappearing filled orders.
- Fail-closed corrupt/partial/stale checks and one consistent recorded NAV.
- Completed-bar guards instead of recording a trading day during the morning.
- Cash-only settlement and per-lot delivery eligibility, including top-ups.
- Shared FIFO tax accounting, explicit reserve reducing NAV, cost taxonomy.
- Quoted execution/marking, gap-stop handling, position/sector enforcement.
- Preserved initial-history correction and separate forward observations.
- Safe publisher after a non-fast-forward daily publication failure.
- External watchdog/incident lifecycle, public deployment probe and calendar alerts.
- Public holdings, prices, calls, journal, methodology, research and forward views.

Recent commits, newest first:

| Commit | Change |
| --- | --- |
| `9e27d1f` | Income scenario, special-session completion guards, weekend checks |
| `5e959d0` | Calendar coverage renewal and new income lot delivery dates |
| `df5def3` | Simultaneous fills tested against position/sector limits |
| `7bbf380` | Return-period annualization, two-point loss reporting, undefined profit factor |
| `7d3055a` | CLI reads current saved calls; narration truthfulness/provenance |
| `f5dcd14` | Watchdog advance calendar-expiry alerts |
| `ec260be` | Focused release acceptance after daily/public verification |

Legacy historical research numbers were not silently recomputed by metrics fixes.
The archive remains unchanged. Old warning text in chronological documents may
describe defects subsequently fixed; use newest evidence, not isolated old prose.

## 7. Income: the exact agreement

User approved an explicit simulation after being told verified credit information
was unavailable. `docs/INCOME_SCENARIO.md` is the precise model specification:
4% illustrative simple annual rate on INR1,000 per previous-close settled LIQUIDBEES
unit, ACT/365, no reinvestment, configured slab/surcharge/cess. Accrues from
September30, 2026 close; first positive interval normally endsOctober1.

It persists under `income_scenario` in existing books/ledger and displays separate
gross/tax/net figures. It never changes recorded NAV, cash, units, allocation,
verified tax reserve or forward returns. It is not an observed yield forecast.
No historical income was backfilled. The September29 handoff books contain no
scenario accrual yet; future genuine daily execution still needs observation.

Verified receipts use `qlab.income` and `config.json`'s optional `income_receipts`.
They require preserved source bytes, hash, dates and attribution. Late receipts
require a documented correction. Calculator rounding is not evidence of credit
date, entitlement or withholding. Paper books have no real demat statement.
Keep unknown real distributions disclosed, but do not freeze the product over them.

## 8. Calendar: current bounds and follow-up

Trading calendar coverage: September18–November7, 2026. Settlement calendar:
September1–December31, 2026. Separate calendars are intentional. Clearing holidays
include November10/24 and December25. No2027 dates have been inferred.

NSE identifies a November8 Sunday Muhurat session; its timing was not available
at the last source review. Do not guess it. `special_sessions` supports date keys
with `source_url` and `completed_after_ist`; use official close plus a vendor buffer.
Both run guard and freshness honor that time. Review special clearing exceptions,
add remaining official holidays and extend coverage when the circular is available.
The watchdog alerts14 days before coverage expiry (trading warning fromOctober24).

Official sources:
- https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf
- https://nsearchives.nseindia.com/content/circulars/CMPT71904.pdf
- https://www.nseindia.com/resources/exchange-communication-holidays/
- https://mf.nipponindiaim.com/InvestorServices/SIDETF/NipponIndia-ETF-Nifty-1D-Rate-Liquid-BeES.pdf

## 9. Hosting, GitHub access and secrets

The project itself is not hosted by ChatGPT. GitHub stores code/state; GitHub Actions
runs jobs; Streamlit Community Cloud hosts the public UI. Switching assistants does
not require a new repository, redeployment or moving book files to a new service.

ChatGPT/Codex's GitHub connector and browser login do **not** grant Claude Code
credentials. Authenticate Claude's environment separately to GitHub as the owner or
authorized collaborator. Use its approved GitHub integration or GitHub CLI login.
Public cloning needs no credential; pushing, dispatching and settings changes do.
Do not place credentials in this public repository or copy tokens into prompts.

| Secret / identity | Purpose |
| --- | --- |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT` | Optional Telegram alerts |
| `ANTHROPIC_API_KEY` | Optional narrator without an OpenAI key |
| `OPENAI_API_KEY` | Optional alternative narrator |
| Actions `GITHUB_TOKEN` | Automatically supplied workflow identity, not a manual secret |
| Streamlit owner's login | Deployment/reboot/settings access |

Optional secret presence/values were **not audited for this handoff**. No secret
values are included. Existing repository secrets stay in GitHub when you change
assistants. Repo settings: https://github.com/Andy7204/dhruva/settings/secrets/actions
No narrator key is required; rule narration is the fallback. A Claude Code
subscription/login should not be assumed to provide the app's Anthropic API key.

## 10. Schedules and verification snapshot

| Automation | Schedule / behavior |
| --- | --- |
| `.github/workflows/daily.yml` | Weekdays18:30IST; weekend23:30IST special-session checks; normal closed days skip |
| `.github/workflows/watchdog.yml` | Daily02:30IST, health and GitHub incident handling |
| `.github/workflows/tests.yml` | Relevant pushes and PRs; dependencies, archive, tests, ledger acceptance |
| Codex `dhruva-official-calendar-update` | Active weekly Sunday12:00 local reminder to review/configure official Muhurat timing |
| Codex `continue-dhruva-hardening-after-usage-reset` | Paused development programme; do not revive |

Codex reminders are outside the repository and do not migrate automatically.
The active calendar reminder has not been disabled by preparing this handoff.
Transfer its ownership/scheduling explicitly to avoid duplicate assistant edits;
then pause/delete it in Codex. Leave GitHub daily/watchdog workflows active.

Observed at handoff (re-check after pulling, do not treat these as live forever):
- Source `9e27d1f`:94 local tests passed; CI36556441099 succeeded.
- Calendar/receipt fix CI36555895099 succeeded.
- Latest observed scheduled daily36475610360 succeeded, producing090de2b.
- Latest observed watchdog36504877696 succeeded.
- Local books: September28, balanced INR69,710.35; aggressive INR30,000;
  total INR99,710.35; zero pending orders in both (HOLD).
- Public UI last browser acceptance was September28; latest source UI tested locally.
  September29 handoff does not certify a new September29 market evaluation.

## 11. Setup and safe operating commands

Use Python3.12 (CI exact version3.12.14) and an isolated environment. On a new machine:

```powershell
git clone https://github.com/Andy7204/dhruva.git
Set-Location dhruva
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m dhruva.freeze
.\.venv\Scripts\python.exe scripts/show_call.py
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

On this machine use `Set-Location Z:\dhruva` instead of cloning over the existing
checkout. Prior Codex bundled Python path was
`C:\Users\adpan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`;
it is an environment detail, not a portable dependency requirement.

Canonical daily command: `python -m dhruva.run_daily`. It fetches data and mutates
paper state: do not run casually alongside scheduled production. Inspect Actions
first, avoid redundant dispatch, and obey the real-time guard. Prefer focused
tests for edits; use the integrated suite when changes warrant it.

Before edits: `git status`, fetch/check remote, preserve local changes. Daily
automation can advance `main`. Pull/rebase only with a clean or safely preserved
worktree; never force-push over generated evidence. Commit actual changes/tests.
Inspect failures and the AGENTS debug playbook before improvising.

## 12. Debug and known limitations

Windows rupee-character failures: use UTF-8 (`PYTHONUTF8=1`, or import qlab).
Wrong200DMA: inspect benchmark cache frequency; never fetch live-used symbols with
`rng='max'` (historically returned monthly data). Use daily5y history when repairing.
Ticker404 may be a delisting; widespread errors may be throttling. Never silently
drop held assets or force health green. App asleep/stale: check Streamlit and actual
Actions publication, not just a cached dashboard. Failed tests deliberately emit
synthetic failure records; distinguish them from real operational failures.

Survivorship/current-universe and adjustment-vintage biases remain. Legacy engine
backtests use same-close execution and pre-tax reporting; live books use next-open
and shared tax reserve. Challenge research has its own audited simulation and is
not an exact replay of current production. Nifty forward comparison is price-only,
untaxed and cost-free, not an investable total-return benchmark. Short forward
history proves neither profit nor robustness. Fee/tax rules are modeled parameters,
not permanent statements of law. Streamlit may sleep; GitHub cron can be delayed.

Research reruns need original input hashes: daily cache refreshes mean today's
cache may not reproduce old reports. Preserve historical results and use the
recorded commit/data evidence before making claims about changes in performance.

## 13. Reading order and stop condition

Read AGENTS fully, this handoff, checklist, FOCUSED_RELEASE and newest progress.
Use ACCOUNTING_REPAIRS, INCOME_SCENARIO, DAILY_PIPELINE, DATA_CONTRACT, LEDGER,
RUN_HEALTH and WATCHDOG for the corresponding subsystem. AUDIT_HISTORY preserves
the complete audit narrative. HARDENING_MISSION and ORIGINAL are historical backlog.

Take over maintenance, verify next genuinely due run and income scenario when
eligible, handle sourced calendar updates. Do not start broad optional work.
Report concretely what passed, what changed and what still depends on external data.
