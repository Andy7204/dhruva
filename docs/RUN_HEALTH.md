# Structured run health

Each canonical attempt records run ID, start/end, actual Git commit, strategy
identity, final status, execution-completed flag, latest data date, decision
status, new-evaluation count, warnings/errors and stage observations. Stages:
archive, ingestion, validation, features, benchmark, portfolio, risk, ledger,
report and optional alerts. Transitions persist immediately in runs/operations.
An exception marks any running stages FAILED and later stages stay NOT_RUN.

FAILED is never converted to NO_ACTION. SKIPPED_NOT_DUE means the time/calendar
guard blocked execution. Successful execution currently ends DEGRADED because
known economic repairs remain; data may separately be VALID_WITH_EXCLUSIONS.
The UI recognizes an execution-completed degraded attempt as the latest completed
pipeline without calling its accounting healthy. Missing runs are watchdog work,
not a success status manufactured by a pipeline that never started.

Verification September24:35 tests pass. A simulated stale benchmark failed during
data_validation, left portfolio_engine NOT_RUN, execution_completed false and
preserved exact error `ValueError: fixture stale benchmark`. Separate interruption
and duplicate tests still pass. This fixture did not replace production records.
Remote after-close observations of the new stage schema are still pending.

Optional Telegram now reports delivered/failed/not-configured instead of ignoring
the Boolean result. A reliable external operational alert remains Phase9; this
document does not claim a Telegram message was delivered.
