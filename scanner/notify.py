"""Change-only notices for the inflection radar, posted to one standing GitHub issue.

Posts when something material happened (fast-lane ticket, state change, new
Stage 3 review, new missed-winner case) and a Friday summary; silent otherwise.
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd

from dhruva.util import atomic_write, canonical

ROOT = Path(__file__).resolve().parents[1]
INF = ROOT/'runs'/'inflection'
MARKER = '<!-- dhruva-inflection -->'
TITLE = '[Dhruva] Inflection radar updates'


def build(session):
    lines, material = [f'**Dhruva inflection radar — {session}** (paper research, not advice)'], False
    fl = INF/'fast_lane.csv'
    if fl.exists():
        t = pd.read_csv(fl)
        t = t[pd.to_datetime(t['date']) >= pd.Timestamp(session)-pd.Timedelta(days=3)]
        if len(t):
            material = True
            lines += ['', 'Fast lane (new material filings):'] + [f"- {e.symbol}: {e.desc} — {e.fast_lane_reasons}" for e in t.itertuples()]
    tr = INF/'transitions.jsonl'
    if tr.exists():
        rows = [json.loads(x) for x in tr.read_text(encoding='utf-8').splitlines() if x.strip()]
        today = [r for r in rows if r['date'] == session and r['from'] != r['to']]
        if today:
            material = True
            lines += ['', 'State changes (paper model portfolio):'] + [
                f"- {r['symbol']}: {r['from']} → {r['to']}" + (f" (₹{r['inr']:,.0f} at ~₹{r['price']})" if r['inr'] else '') + f" — {r['reason']}" for r in today]
    ms = INF/'audit'/'missed.jsonl'
    if ms.exists():
        new = [json.loads(x) for x in ms.read_text(encoding='utf-8').splitlines() if x.strip() and f'"detected_on": "{session}"' in x]
        if new:
            material = True
            lines += ['', f'Missed-winner audit: {len(new)} new'] + [f"- {x['symbol']} +{x.get('excess_return_pct')}% vs Nifty 500 since {x['move_start']}: {x['diagnosis']}" for x in new[:8]]
    q = INF/'stage3_queue.json'
    if q.exists():
        items = json.loads(q.read_text(encoding='utf-8'))
        if items:
            lines += ['', 'Waiting for Stage 3 underwriting: ' + ', '.join(f"{x['symbol']} ({x['trigger']})" for x in items)]
    weekly = date.fromisoformat(session).weekday() == 4
    if weekly and not material:
        st = pd.read_csv(INF/'stage2.csv') if (INF/'stage2.csv').exists() else pd.DataFrame()
        if len(st):
            lines += ['', 'Weekly summary — finalists: ' + ', '.join(st.loc[st['finalist'], 'symbol'])]
    lines += ['', 'Full report: runs/inflection/report.md']
    kind = 'CHANGE' if material else 'WEEKLY' if weekly else 'NONE'
    note = {'kind': kind, 'as_of': session, 'text': '\n'.join(lines)}
    (INF/'notice.json').write_text(json.dumps(note, indent=1, ensure_ascii=False), encoding='utf-8')
    return note


def post(root=ROOT, client=None):
    path = root/'runs/inflection/notice.json'
    if not path.exists(): return {'status': 'NOTHING_TO_SEND'}
    note = json.loads(path.read_text(encoding='utf-8'))
    if note['kind'] == 'NONE': return {'status': 'NOTHING_TO_SEND'}
    receipt = root/'runs/alerts/inflection-last.json'
    if receipt.exists() and json.loads(receipt.read_text(encoding='utf-8')).get('as_of') == note['as_of']:
        return {'status': 'ALREADY_SENT'}
    from dhruva.alerts import GitHub
    client = client or GitHub()
    issues = client.request('GET', '/issues?state=open&per_page=100')
    issue = next((i for i in issues if i.get('title') == TITLE and MARKER in (i.get('body') or '')), None)
    if issue is None:
        issue = client.request('POST', '/issues', {'title': TITLE, 'assignees': [client.repo.split('/')[0]],
                                                   'body': MARKER+'\nStanding thread for inflection-radar calls and updates. Paper research, not advice.'})
    client.request('POST', f"/issues/{issue['number']}/comments", {'body': note['text']})
    atomic_write(receipt, canonical({'as_of': note['as_of'], 'issue': issue['number']})+b'\n')
    return {'status': 'SENT', 'issue': issue['number']}


if __name__ == '__main__':
    print(json.dumps(post()))
