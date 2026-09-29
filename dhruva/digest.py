"""Change-only paper call notices plus a Friday weekly summary.

Daily evaluation continues; people are only notified when something changed
(a book decides a new allocation) or once a week on Fridays.
"""
from datetime import date
import json
import os
from pathlib import Path

from dhruva.util import atomic_write, canonical

ROOT = Path(__file__).resolve().parents[1]
MARKER = '<!-- dhruva-digest -->'
TITLE = '[Dhruva] Paper call updates'


NAMES = {'MIDMOM50': 'Midcap Momentum 50', 'MOM30': 'Momentum 30', 'GOLD': 'gold', 'NDX': 'Nasdaq-100',
         'LIQ': 'liquid fund', 'N50': 'Nifty 50'}


def _mix(weights):
    return ', '.join(f'{NAMES.get(a, a)} {w*100:.0f}%' for a, w in sorted(weights.items(), key=lambda x: -x[1]) if w > 0.005) or 'cash'


def build(previous, books, ccy='₹'):
    """Return {'kind': CHANGE|WEEKLY|NONE, 'as_of', 'text'} from book summaries only."""
    as_of = next(iter(books.values()))['as_of']
    bench = books.get('N50', {}).get('liquidation_value')
    changes = []
    for bid, b in books.items():
        if bid == 'N50': continue
        if b.get('pending_target'):
            old = (previous.get(bid) or {}).get('weights') or {}
            target = b['pending_target']
            if any(abs(target.get(a, 0)-old.get(a, 0)) > 0.02 for a in set(target) | set(old)):
                changes.append(f"{b['label']}: rebalance at the next close to {_mix(target)}")
    lines = [f'Dhruva PAPER ONLY — {as_of}']
    if changes:
        kind = 'CHANGE'; lines += ['New paper calls:'] + ['- '+c for c in changes]
    elif date.fromisoformat(as_of).weekday() == 4:
        kind = 'WEEKLY'; lines.append('Weekly summary: no new calls.')
    else:
        kind = 'NONE'; lines.append('No change.')
    for bid, b in books.items():
        lines.append(f"{b['label']}: {ccy}{b['liquidation_value']:,.0f} after tax"
                     + (f" ({(b['liquidation_value']/bench-1)*100:+.2f}% vs Nifty 50)" if bench and bid != 'N50' else '')
                     + f"; holding {_mix(b['weights'])}")
    lines.append('Paper research, not investment advice.')
    return {'kind': kind, 'as_of': as_of, 'text': '\n'.join(lines)}


def post(root=ROOT, client=None):
    """Comment on one standing issue, at most once per session date."""
    path = root/'runs/digest.json'
    if not path.exists():
        return {'status': 'NOTHING_TO_SEND'}
    digest = json.loads(path.read_text(encoding='utf-8'))
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
