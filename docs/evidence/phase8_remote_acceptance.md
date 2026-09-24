# Phase 8 remote acceptance — September 24, 2026

GitHub API observations after execution, not fabricated historical timestamps:

- Normal independent watchdog run 36016354838: success.
- Synthetic external alert run 36016083742: success. Issue #3 was created,
  reused for the repeated failure, and closed on recovery.
  https://github.com/Andy7204/dhruva/issues/3
- Initial test 36015758732 failed: `CREATED, CREATED, NO_INCIDENT` instead of
  `CREATED, ALREADY_OPEN, RECOVERED`. GitHub's immediate issue listing lagged
  creation. Direct issue receipts and uncached listing fixed this; regression
  coverage includes stale listings. Test issues #1 and #2 were closed.
- CI 36016441138 passed at f1024b3.
- Daily 36015761872 calculated September24, but its older publication code
  failed: `! [rejected] main -> main (fetch first)`. No generated commit reached
  main. Its artifact contains operations only, not the uncommitted ledger/cache.
  Do not treat its lost segment as published evidence or recreate its timestamp.
  f1024b3 adds safe rebasing over code-only changes, refuses concurrent generated
  state overwrites, and uploads all generated evidence. A new run remains due.

Phase8 proves operational watchdog and external delivery, not repaired accounting.
