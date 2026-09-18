# Permanent paper evidence

`dhruva/ledger.py` writes one immutable segment per evaluation under
`runs/ledger/<track>/segments/`. Each segment binds all events and the full
portfolio bundle to the previous segment hash. Event identity and content hash
are verified on read. Input snapshots are compressed and addressed by SHA-256.
Required provenance fields are validated; only PAPER/SHADOW modes are allowed.

A process lock serializes writers. Segment publication and checkpoints use
same-directory atomic replacement, flush and fsync. Existing segments are never
overwritten by the application. Duplicate keys with identical content return
the original; conflicting content fails. Corrections append an event referencing
the original ID. A separate checkpoint detects tail deletion; a remote Git head
provides an external anchor. An administrator could rewrite both hashes and Git;
do not describe this as cryptographically unforgeable or WORM storage.

The daily v1 wrapper captures every per-symbol evaluation for both books plus
configuration, commit, input snapshot, pre/post state, scheduled intent and prices.
It writes the ledger before publishing mutable book projections. A repeated date
returns the original captured bundle, even when cached quotes have changed.
Ledger failure prevents book publication. Later phases harden full-run transactions
and operational health. V1 economics remain unchanged and explicitly flawed.

Legacy observations use `IMPORTED_LEGACY_OBSERVATION`. Their original generation
time is unknown. Bar cutoffs are explicitly date-only and unverified until the
new data contract exists. Current marked weights and pre-cost order intent are
labelled; they are not falsely presented as historical closing/guaranteed weights.

Persistence: the existing daily workflow already commits all of `runs/`, including
segments and snapshots. A clean Git checkout restores the complete ledger, so
Streamlit does not own the only copy. An unsuccessful push is not durable remote
publication; subsequent phases must report that failure.

Acceptance fixture: `python scripts/ledger_acceptance.py`. Its namespace is
`acceptance_test_only`, never used for performance. Run it in a new process or
fresh remote checkout: the same head/event count must return with no new event.
`python -m unittest discover -s tests -v` tests restart, duplicate conflicts,
corrections, tampering, truncation, input corruption and a checkpoint crash.
