"""Print saved, health-checked live paper calls; never recalculate decisions."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import qlab  # UTF-8 console
from dhruva.health import inspect


def render_call(health):
    lines=['Dhruva — PAPER ONLY', 'Status: '+health['status']]
    if health['problems']:
        lines.append('CURRENT CALL WITHHELD: saved evidence is stale, invalid or incomplete.')
        lines.extend(health['problems'])
        return '\n'.join(lines)
    if health['status']!='OPERATIONAL':
        lines.append('CURRENT CALL WITHHELD: operational verification incomplete.')
        return '\n'.join(lines)
    for book in health['books']:
        state=book['state']
        scheduled=[o for o in state['orders'] if o['status']=='scheduled']
        action=', '.join(sorted({o['side'] for o in scheduled})) if scheduled else 'HOLD'
        lines.append(f"{book['name'].upper()} | {book['as_of']} | {action} | NAV ₹{book['value']:,.2f}")
        lines.append(('Market filter: risk-on.' if state.get('risk_on') else 'Market filter: defensive.')+
                     f" Next allocation review: {state.get('next_rebalance_in','unknown')} trading sessions; stops checked daily.")
        for order in scheduled:
            lines.append(f"  {order['side']} {order['symbol']} — pending paper intent; {order.get('reason') or order.get('pending_reason','next eligible open, subject to execution checks')}")
    lines.extend(health['warnings'])
    lines.append('Saved paper decisions only; no real orders or predictions.')
    return '\n'.join(lines)


def main():
    health=inspect(ROOT,verify_snapshots=False)
    print(render_call(health))
    return 0 if health['status']=='OPERATIONAL' and not health['problems'] else 1


if __name__=='__main__': raise SystemExit(main())
