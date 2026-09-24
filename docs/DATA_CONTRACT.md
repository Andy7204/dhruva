# Daily data contract and causality repairs

September24: real cache check for expected completed session September23 returned
VALID_WITH_EXCLUSIONS,500/504 symbols (99.206%). Exclusions: HEG.NS and INDIGRID.NS
stale; ICICIAMC.NS and MEESHO.NS fewer than200 sessions. Held assets and benchmark
passed. Evidence: `runs/data_quality.json` and archived
`docs/evidence/phase6_data_quality.json`. No trading state was changed by this check.

Acquired/cache-merged raw bars are separate from rowwise validated data, adjusted
OHLC transforms and signal features. Immutable per-evaluation snapshots preserve
the raw bars through cutoff and the quality report that chose the eligible set.
Capture time is labelled capture time, not fabricated provider retrieval time.
Yahoo bars are vendor observations, not an independently certified exchange feed.

Contract: require OHLCV schema, unique dates, finite positive possible prices,
nonnegative volume, latest completed session, at least200 observations, nonzero
latest traded volume (index exception), and no latest adjusted jump above50%.
An unfinished future bar is explicitly excluded. Historical impossible rows are
removed rowwise; historical jumps and adjustment-factor changes are flagged,
not deleted based on later prices. Fail if a held asset or benchmark is invalid,
an expected recovery benchmark session is missing, or eligible coverage is below
95% (configurable). Other unavailable symbols are explicitly ineligible and any
pending buys are cancelled with a data-exclusion reason on the next new capture.
Missing current held prices never advance the daily book using entry-cost marks.

The centered median cleaner was removed. ATR, ADX and Donchian price levels now
use the same adjusted OHLC units as prices. Prefix tests show future appended bars
do not alter past cleaned rows/features. Active book basket overrides no longer
erase the common defensive-asset exclusion list. Cache writes are atomic.

Costs/tax/execution were audited but remain explicitly pending in the error
register; data fixes do not make their economic results trustworthy by themselves.
Upcoming phases retain this warning until their repair tests and reconciliation
are complete. This contract also does not cure current-constituent survivorship,
missing delisted outcomes, historical revision vintages or adjusted-unit dividend
accounting. No point-in-time fundamental database exists. These are disclosed
limitations, not solved by changing a status label.

Validation:34 tests passed before the small evidence-metadata/health integration;
the final suite result is recorded in HARDENING_PROGRESS. Tests cover missing and
stale benchmark/held inputs, outage fallback, malformed schema, duplicate dates,
zero volume, corrupt latest OHLC, unfinished-bar exclusion, index volume, causal
prefixes and adjusted ATR. Production after-close execution of these new data
rules remains to be observed; the direct real-cache check was read-only on books.
