# Dhruva handoff sheet

September29, 2026. Owner after transfer: user / Claude Code. Evidence is a snapshot.

| Priority | Item | Current status | Next action / acceptance |
| --- | --- | --- | --- |
| First | Open project | `Z:\dhruva`, public GitHub Andy7204/dhruva | Read CLAUDE.md and AGENTS; inspect clean status and remote changes |
| First | GitHub access | Codex connector does not transfer | Authenticate Claude separately; verify read access, then push access only when needed |
| First | Preserve running service | Existing GitHub + Streamlit deployment | Keep daily/watchdog active; do not reset/redeploy unnecessarily |
| First | Current health | Last observed books Sep28, INR99,710.35 | Inspect latest Actions, ledger/date/current public page; distinguish not-due from stale |
| Next due | Income scenario | Code/UI tested, CI passed; prospective from Sep30close | Observe genuine Oct1-or-later run; estimate persists once, stays outside NAV/cash/units |
| Next due | Daily reliability | Sep28 scheduled run and Sep29 watchdog succeeded | Check next normal run; fix concrete errors, no redundant dispatch |
| By Oct24 warning | Calendar ownership | Codex weekly reminder active | Transfer reminder to chosen environment; then disable Codex copy to avoid dual ownership |
| Before Nov8 | Muhurat session | Timing unpublished at last review; code supports it | Official timing+buffer, source URL, remaining holidays, clearing review, tests, commit/push |
| Before year end | 2027 calendars | Not configured | Source official trading and clearing calendars; no extrapolation |
| If authoritative evidence arrives | Actual distribution receipts | Still unverified; estimate is not a substitute receipt | Reconcile dates/units/withholding; source hash; explicit historical correction if needed |
| Optional | Telegram / AI narration | Env wiring exists; secret presence not checked | Add named secrets only if desired; no key required for rule narration |
| Maintenance | Fee/tax/vendor/hosting changes | Explicit known dependencies | Review when rules/providers change or watchdog reports an incident |
| Not authorized by old plan alone | New strategy/research/architecture | Mandatory phases cancelled | Ask user for new scope; do not resume26/10phase checklist |

## Copy/paste starter prompt

```text
Take over Dhruva in Z:\dhruva (or clone https://github.com/Andy7204/dhruva if this
machine does not have it). Read CLAUDE.md, AGENTS.md fully, docs/CLAUDE_HANDOFF.md,
docs/HANDOFF_CHECKLIST.md and the newest HARDENING_PROGRESS.md entries first.
This is an already-live paper-only app. Preserve deterministic decisions, no
look-ahead, honest costs/tax and original ledger/archive evidence. Repair in place.
The mandatory ten-phase programme is cancelled. Do not restart it.
First inspect local changes, latest GitHub Actions and current saved/public state;
avoid redundant daily runs. Verify the prospective income scenario on a genuinely
eligible daily run. Keep it separate from NAV/verified receipts. Maintain official
exchange/clearing calendars without inventing November8 Muhurat hours or2027 dates.
Tell me whether your GitHub authentication works and which next concrete action is
needed. Coordinate the calendar reminder handoff; Codex currently has an active
weekly reminder that must not be left editing concurrently after transfer.
Use minimal credits and plain English. Do not reset books, copy secrets into files,
change strategy or undertake a broad rewrite. Finish bounded fixes with tests and
evidence. Normal daily/watchdog GitHub automation must continue.
```

## Transfer boundaries

Included in Git: code, config, docs, tests, price cache, saved books, ledger,
historical reports/research and workflow definitions. Git history preserves changes.

Not included: ChatGPT/Claude accounts, connector grants, browser sessions, GitHub
secret values, Streamlit login, Codex local reminders. These need separate access
or an explicit scheduling handover. No need to disclose a password or token in chat.

This documentation prepares transfer; it does not install Claude Code, authenticate
it, copy accounts or disable Codex reminders automatically.
