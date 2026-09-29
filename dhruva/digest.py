"""Change-only paper call notices plus a Friday weekly summary.

Daily evaluation continues; people are only notified when something changed
(new paper orders, fills, market filter or circuit breaker flips) or once a week.
"""
from datetime import date
import json
import os
from pathlib import Path

from dhruva.ledger import atomic_write, canonical

ROOT = Path(__file__).resolve().parents[1]
MARKER = '<!-- dhruva-digest -->'
TITLE = '[Dhruva] Paper call updates'


def build(previous, results, ccy='₹'):
    """Return {'kind': CHANGE|WEEKLY|NONE, 'as_of', 'text'} from saved states only."""
    as_of = results[0]['state']['as_of']
    changes = []
    for r in results:
        name, st = r['name'], r['state']
        old = previous.get(name) or {}
        for o in st['orders']:
            if o['status'] == 'scheduled' and o.get('decided_date') == as_of:
                changes.append(f"{name}: new paper {o['side']} {o['symbol']} for the next open"
                               + (f" ({o['reason']})" if o.get('reason') else ''))
            if o.get('fill_date') == as_of and o['status'] == 'filled':
                changes.append(f"{name}: filled {o['side']} {o['symbol']} {o.get('qty')} @ {o.get('fill_price')}")
        if old and bool(old.get('risk_on')) != bool(st.get('risk_on')):
            changes.append(f"{name}: market filter turned {'ON (stock entries allowed)' if st.get('risk_on') else 'OFF (defensive)'}")
        if old and bool(old.get('breaker')) != bool(st.get('breaker')):
            changes.append(f"{name}: circuit breaker {'ACTIVE' if st.get('breaker') else 'released'}")
    nav = sum(r['state']['history'][-1][1] for r in results)
    week_ago = [sum(v for d, v in r['state']['history'][-6:-5]) for r in results]
    lines = [f'Dhruva PAPER ONLY — {as_of} — total recorded NAV {ccy}{nav:,.2f}']
    if changes:
        kind = 'CHANGE'; lines += ['What changed:'] + ['- '+c for c in changes]
    elif date.fromisoformat(as_of).weekday() == 4:
        kind = 'WEEKLY'
        lines.append('Weekly summary: no trades or signal changes this session.')
        if all(week_ago):
            lines.append(f'Change over the last five recorded sessions: {(nav/sum(week_ago)-1)*100:+.2f}%')
    else:
        kind = 'NONE'; lines.append('No change.')
    for r in results:
        st = r['state']
        lines.append(f"{r['name']}: {len(st['holdings'])} holdings, cash {ccy}{st['cash']:,.0f}, "
                     f"next allocation review in {st.get('next_rebalance_in', '?')} sessions")
    return {'kind': kind, 'as_of': as_of, 'text': '\n'.join(lines)}


def post(root=ROOT, client=None):
    """Comment on one standing issue, at most once per session date."""
    digest = json.loads((root/'runs/digest.json').read_text(encoding='utf-8'))
    if digest['kind'] == 'NONE':
        return {'status': 'NOTHING_TO_SEND'}
    receipt = root/'runs/alerts/digest-last.json'
    if receipt.exists() and json.loads(receipt.read_text(encoding='utf-8')).get('as_of') == digest['as_of']:
        return {'status': 'ALREADY_SENT'}
    from dhruva.alerts import GitHub
    client = client or GitHub()
    issues = client.request('GET', '/issues?state=open&per_page=100')
    issue = next((i for i in issues if i.get('title') == TITLE and MARKER in (i.get('body') or '')), None)
    if issue is None:
        issue = client.request('POST', '/issues', {'title': TITLE, 'assignees': [client.repo.split('/')[0]],
            'body': MARKER+'\nStanding thread: one comment when paper calls change, plus a Friday summary. Paper only; not advice.'})
    client.request('POST', f"/issues/{issue['number']}/comments", {'body': digest['text']})
    atomic_write(receipt, canonical({'as_of': digest['as_of'], 'issue': issue['number']})+b'\n')
    return {'status': 'SENT', 'issue': issue['number']}


if __name__ == '__main__':
    print(json.dumps(post()))
