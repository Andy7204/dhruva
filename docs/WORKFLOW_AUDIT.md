# Phase 3 — workflow audit and hardening

Main workflow: `.github/workflows/daily.yml`, default branch `main`, weekdays
13:00 UTC = 18:30 IST, plus manual dispatch. Existing manual run35184975533 and
scheduled run35252434924 succeeded; see Phase0 evidence. The scheduled run was
over four hours late. GitHub documents possible schedule delays and even dropped
queued runs: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
The requested nominal schedule is retained; it is not a timing SLA.

Changes: fixed action commit SHAs (resolved from official repository tag refs),
Python3.12.14, full37-package dependency closure, pip retries/timeouts, test job,
frozen-code verification before execution, durable job/attempt evidence on failure,
30-day artifact fallback, and bounded non-force push retries. `contents:write`
applies only to the daily publisher; tests have read-only permission. Daily runs
remain serialized and have a60-minute timeout. Concurrent human pushes can fail
publication safely; no forced history overwrite or automatic unsafe data rebase.

`scripts/daily_run.py` is still the sole operational CLI. It wraps the frozen
engine with `dhruva.operations`, preserving failures instead of swallowing them.
Calls before16:30 IST or on known non-trading days do not advance the paper book.
That is `SKIPPED_NOT_DUE`, not a no-signal investment conclusion. Completed
execution is labelled `COMPLETED_UNVERIFIED_DATA` until data validation is built;
it must not be represented as healthy. Full structured stages arrive in Phase7.

Calendar: the official NSE capital-market circular
https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf supplies dates.
Configured prospective coverage is Sep18–Oct31,2026. Later dates fail closed
pending updated circular review, including November8 special-session timing.
This scheduling calendar is not a settlement calendar; v1 settlement remains a
documented bug pending a new execution version. A weekday cron can run on a
holiday but the application records an explicit no-run reason.

Secrets: no user-added secret is required for the basic paper run or rule narrator.
GitHub supplies its job token. Optional `TELEGRAM_TOKEN` and `TELEGRAM_CHAT` must
both exist for Telegram; optional `ANTHROPIC_API_KEY` enables non-OpenAI narration,
or `OPENAI_API_KEY` is an alternative. Values must never be printed. Optional
secret presence/delivery is not asserted by this audit. No available connector
reads secret metadata. A read-only GitHub settings check on September18 showed
no repository or environment secrets. None are required for basic operation;
Telegram/LLM delivery is therefore not configured or claimed. The successful
remote publisher confirms its GitHub-supplied token has the necessary access.

Known limits: artifact retention is not permanent; Git is the durable copy.
Runner termination before the always step cannot self-report, requiring Phase8
watchdog. External failure alerts are not yet implemented (Phase9). Hosting
freshness is Phase4. Clean Linux install/manual hardened run evidence must be
recorded before Phase3 is complete; YAML and local tests alone are insufficient.

## Verified remote evidence

- Clean Linux dependency install, all16 tests, freeze verification and restored
  ledger fixture passed in run35305417648:
  https://github.com/Andy7204/dhruva/actions/runs/35305417648
- Hardened manual daily run35305448785 succeeded and committed evidence in
  `e45caaf`. It correctly recorded `SKIPPED_NOT_DUE / BEFORE_COMPLETED_SESSION`
  at04:03 UTC (09:33 IST), rather than processing an unfinished session:
  https://github.com/Andy7204/dhruva/actions/runs/35305448785
- `runs/operations/35305448785.json` and `job-35305448785.json` are the actual
  remote output, retrieved by fast-forward Git fetch. Artifact publication passed.
- This manual run did not refresh prices. Existing scheduled refresh is evidenced
  separately by run35252434924; the hardened after-close path still needs its
  own real run during Phase4 acceptance. No false green data claim is made.
