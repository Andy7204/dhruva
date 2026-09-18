"""Print today's call for each book in plain text (reads runs/todays_call_*.json).

    python scripts/show_call.py

Run after the daily update to see the decisions.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import qlab  # noqa: F401  (forces UTF-8 stdout for the rupee sign)

R = "₹"
files = sorted((ROOT / "runs").glob("todays_call_*.json"))
if not files and (ROOT / "runs" / "todays_call.json").exists():
    files = [ROOT / "runs" / "todays_call.json"]
if not files:
    print("No call yet — run: python scripts/daily_run.py")
    sys.exit(0)


def show(c, book):
    print(f"\n{'='*6} {book.upper()} — TODAY'S CALL {c['date']} {'='*6}")
    print(("RISK-ON" if c["risk_on"] else "RISK-OFF")
          + f"  (Nifty {c['nifty']:.0f} vs 200-DMA {c['nifty_ma']:.0f})")
    tgt = ", ".join(f"{k} {v}%" for k, v in (c.get("target_defensive") or {}).items())
    print(f"Target: {c.get('target_equity_pct','?')}% momentum stocks"
          + (f" + diversifiers {tgt}" if tgt else ""))
    if c.get("buys"):
        print("BUY:")
        for b in c["buys"]:
            print(f"  {b['symbol']:12s} {b['qty']:>4d}sh @{R}{b['price']:.1f} = {R}{b['invest']:,.0f}"
                  f"  stop {R}{b['stop']:.1f} (risk {R}{b['risk_rupees']:,.0f})  win-case ~{R}{b['win_case_rupees']:,.0f}")
    elif not c["risk_on"]:
        print("Stay defensive — no new stock buys.")
    if c.get("defensive_basket"):
        print("Diversifiers held: " + ", ".join(f"{d['symbol']} {R}{d['value']:,.0f}" for d in c["defensive_basket"]))
    sells = [a for a in c.get("holdings_actions", []) if a["action"] in ("SELL", "TRIM/WATCH")]
    for a in sells:
        print(f"  {a['action']}: {a['symbol']} — {a['reason']}")


for f in files:
    book = f.stem.replace("todays_call_", "") or "main"
    show(json.loads(f.read_text()), book)
print("\n(Research only, not advice.)")
