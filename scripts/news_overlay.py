"""LIVE news overlay for today's call — a human review step, NOT a backtested signal.

Reads runs/todays_call.json and pulls current Google-News headlines for each name
the call touches (buys, holdings), flagging anything that looks material (RISK) or
earnings-related. Use it to eyeball 'is anything blowing up before I act?'.

    python scripts/news_overlay.py

Cannot be backtested (no free point-in-time news history) — treat as unproven.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qlab import news as N  # noqa: E402

files = sorted((ROOT / "runs").glob("todays_call_*.json"))
if not files and (ROOT / "runs" / "todays_call.json").exists():
    files = [ROOT / "runs" / "todays_call.json"]
if not files:
    print("No call yet — run: python scripts/daily_run.py")
    sys.exit(0)

# names to scan: buys + current stock holdings across all books
tickers = []
for f in files:
    c = json.loads(f.read_text())
    tickers += [b["symbol"] for b in c.get("buys", [])]
    tickers += [a["symbol"] for a in c.get("holdings_actions", [])]
tickers = list(dict.fromkeys(tickers))  # dedupe, keep order
if not tickers:
    # risk-off with no stock holdings — scan the current top watchlist instead
    print("No stock positions/buys today (risk-off). Nothing to news-check.")
    sys.exit(0)

print("=== LIVE NEWS OVERLAY (unvalidated — for review only) ===")
for t in tickers:
    sym = t if t.endswith(".NS") else t + ".NS"
    r = N.check(sym)
    mark = {"RISK": "⚠ RISK", "EARNINGS": "\U0001f4c8 EARNINGS", "quiet": "  quiet"}[r["flag"]]
    print(f"\n{mark}  {r['name']} ({t})")
    for h in r["headlines"][:4]:
        print(f"   [{h['date']}] {h['title'][:90]}")
print("\nReminder: this is a live sanity-check, not part of the validated edge.")
