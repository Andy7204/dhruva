"""Stage 3: Claude deep-underwriter over the Stage 2 finalists.

Runs only where something changed, to control cost:
- no thesis record yet; or
- Stage 2 score moved 5+ points since the last review; or
- a new result/presentation/order/capacity filing since the last review; or
- the last review is 30+ days old.
At most UNDERWRITER_MAX (default 3) companies per run, best Stage 2 score first.

Each review appends to runs/inflection/db/<SYMBOL>.json (history is never
rewritten) and the daily report is rebuilt. Capital: INR10,000 credited on the
first session of each month; holdings change only through confirmed trades in
runs/inflection/confirmed_trades.jsonl, never from a recommendation.

    python -m underwriter.run --session 2026-09-30
"""
import argparse
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INF = ROOT/'runs'/'inflection'
DB = INF/'db'
MODEL = 'claude-opus-5-5'
MONTHLY = 10_000


def capital(session):
    """Credit monthly cash once per month; apply owner-confirmed trades only."""
    path = INF/'capital.json'
    cap = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
        'monthly_inr': MONTHLY, 'credited_months': [], 'cash_inr': 0., 'holdings': {}, 'applied_trades': 0}
    month = session[:7]
    if month not in cap['credited_months'] and session >= '2026-10-01':
        cap['credited_months'].append(month); cap['cash_inr'] += MONTHLY
    trades = INF/'confirmed_trades.jsonl'
    if trades.exists():
        rows = [json.loads(x) for x in trades.read_text(encoding='utf-8').splitlines() if x.strip()]
        for t in rows[cap['applied_trades']:]:  # {"date","symbol","side":"BUY|SELL","qty","price","fees"}
            value = t['qty']*t['price']
            h = cap['holdings'].setdefault(t['symbol'], {'qty': 0, 'cost_inr': 0.})
            if t['side'] == 'BUY':
                cap['cash_inr'] -= value+t.get('fees', 0); h['qty'] += t['qty']; h['cost_inr'] += value+t.get('fees', 0)
            else:
                avg = h['cost_inr']/h['qty'] if h['qty'] else 0
                cap['cash_inr'] += value-t.get('fees', 0); h['qty'] -= t['qty']; h['cost_inr'] -= avg*t['qty']
                if h['qty'] <= 0: cap['holdings'].pop(t['symbol'])
        cap['applied_trades'] = len(rows)
    path.write_text(json.dumps(cap, indent=1), encoding='utf-8')
    return cap


def record(symbol):
    path = DB/f'{symbol}.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def due(row, rec, session, filings):
    if rec is None: return 'first review'
    last = rec['reviews'][-1]
    if abs(row['stage2_score']-last.get('stage2_score', 0)) >= 5: return 'Stage 2 score moved 5+ points'
    new = [a for a in filings.get(row['symbol'], []) if str(a.get('time'))[:10] > last['date']]
    if new: return 'new filing: '+new[0]['desc']
    if (date.fromisoformat(session)-date.fromisoformat(last['date'])).days >= 30: return '30-day refresh'
    return None


def underwrite(client, symbol, dossier, previous, context):
    system = (ROOT/'prompts/underwriter.md').read_text(encoding='utf-8')
    user = (f'# Stage 2 dossier\n{dossier}\n\n# Previous thesis record\n'
            f'{json.dumps(previous, indent=1) if previous else "none (first review)"}\n\n'
            f'# Priority list and capital\n{json.dumps(context, indent=1)}\n\n'
            f'Underwrite {symbol} now. Finish with the single JSON block.')
    tools = [{'type': 'web_search_20260209', 'name': 'web_search', 'max_uses': 8},
             {'type': 'web_fetch_20260209', 'name': 'web_fetch', 'max_uses': 6}]
    messages = [{'role': 'user', 'content': user}]
    usage = {'input': 0, 'output': 0}
    for _ in range(6):  # resume pause_turn a bounded number of times
        with client.beta.messages.stream(
                model=MODEL, max_tokens=64000, system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
                thinking={'type': 'adaptive'}, output_config={'effort': 'high'}, tools=tools, messages=messages,
                betas=['server-side-fallback-2026-07-01'], fallbacks='default') as stream:
            response = stream.get_final_message()
        usage['input'] += response.usage.input_tokens; usage['output'] += response.usage.output_tokens
        if response.stop_reason != 'pause_turn': break
        messages = [messages[0], {'role': 'assistant', 'content': response.content}]
    if response.stop_reason == 'refusal':
        raise RuntimeError(f'Model declined: {getattr(response.stop_details, "category", None)}')
    text = '\n'.join(b.text for b in response.content if b.type == 'text')
    match = re.findall(r'```json\s*(\{.*?\})\s*```', text, re.S)
    if not match:
        raise ValueError('No JSON block in underwriter answer')
    result = json.loads(match[-1])
    for key in ('score', 'status', 'action', 'thesis', 'scenarios', 'kill_conditions', 'sources'):
        if key not in result: raise ValueError(f'Underwriter answer missing {key}')
    return result, text, usage


def _md(v):
    return '—' if v is None or (isinstance(v, float) and v != v) else v


def report(session, stage2, cap):
    """Daily report: fast lane, state changes, positions, radar, finalists, audit, final output."""
    from underwriter import state as ST
    pos = ST.load()
    rows = []
    for path in sorted(DB.glob('*.json')):
        rec = json.loads(path.read_text(encoding='utf-8')); r = rec['reviews'][-1]; prev = rec['reviews'][-2] if len(rec['reviews']) > 1 else None
        res = r['result']
        rows.append({'symbol': rec['symbol'], 'conf': res.get('confirmation_score') or res['score']['total'],
                     'prev': (prev['result'].get('confirmation_score') or prev['result']['score']['total']) if prev else None,
                     'disc': pos.get(rec['symbol'], {}).get('discovery'), 'ev': res.get('ev_2y_pct'), 'status': res['status'],
                     'state': pos.get(rec['symbol'], {}).get('state', res.get('proposed_state', '')), 'date': r['date'], 'r': res,
                     'discovered': rec['discovered'], 'discovery_price': rec['discovery_price']})
    rows.sort(key=lambda x: -(x['conf'] or 0))
    L = [f'# Dhruva inflection report — {session}', '',
         'Paper research, not investment advice. The model portfolio is paper; your holdings change only after you confirm a trade.', '']
    fl = INF/'fast_lane.csv'
    L += ['## Fast lane (material filings this week)']
    if fl.exists():
        t = pd.read_csv(fl)
        L += [f"- {e.symbol} {e.date}: {e.desc} — {e.fast_lane_reasons} (price ₹{_md(e.price)})" for e in t.itertuples()] or ['- none']
    else:
        L.append('- none')
    trans = pd.read_json(INF/'transitions.jsonl', lines=True) if (INF/'transitions.jsonl').exists() else pd.DataFrame()
    today = trans[trans['date'].astype(str) == session] if len(trans) else trans
    L += ['', '## State changes today', '| Company | From | To | Paper amount | Price | Reason |', '|---|---|---|---:|---:|---|']
    L += [f"| {t['symbol']} | {t['from']} | {t['to']} | ₹{t['inr']:,.0f} | {_md(t['price'])} | {t['reason']} |" for _, t in today.iterrows()] or ['| none | | | | | |']
    L += ['', '## Positions by state (paper model portfolio)',
          '| Company | State | Since | Paper invested | Discovery | Confirmation | EV 2y % | Last reason |', '|---|---|---|---:|---:|---:|---:|---|']
    order = {s: i for i, s in enumerate(('CORE', 'BUILD', 'STARTER', 'HOLD', 'TRIM', 'RESEARCH', 'EXIT', 'DISCOVER'))}
    for sym, p in sorted(pos.items(), key=lambda kv: order.get(kv[1].get('state'), 9)):
        if p.get('state') == 'DISCOVER': continue
        L.append(f"| {sym} | {p['state']} | {p.get('since', '')} | ₹{sum(e['inr'] for e in p.get('entries', [])):,.0f} | {_md(p.get('discovery'))} | "
                 f"{_md(p.get('confirmation'))} | {_md(p.get('ev_2y_pct'))} | {p.get('last_reason', '')} |")
    L += ['', '## Underwritten radar (latest review, by Confirmation score)',
          '| Company | Confirmation | Prev | Discovery | EV 2y % | Status | State | Last review |', '|---|---:|---:|---:|---:|---|---|---|']
    L += [f"| {x['symbol']} | {x['conf']} | {_md(x['prev'])} | {_md(x['disc'])} | {_md(x['ev'])} | {x['status']} | {x['state']} | {x['date']} |" for x in rows]
    L += ['', '## Stage 2 finalists (quantitative; the Stage 3 queue picks from here)']
    for r in stage2[stage2['finalist']].itertuples():
        L.append(f"- {r.symbol} ({r.industry}): discovery {_md(getattr(r, 'discovery_score', None))}, confirmation {r.stage1_score}, source {getattr(r, 'source', '')}")
    q = INF/'stage3_queue.json'
    if q.exists():
        items = json.loads(q.read_text(encoding='utf-8'))
        L += ['', '## Stage 3 queue (underwritten in Claude Code sessions)'] + ([f"- {x['symbol']}: {x['trigger']}" for x in items] or ['- empty'])
    miss = INF/'audit'/'missed.jsonl'
    if miss.exists():
        m = [json.loads(x) for x in miss.read_text(encoding='utf-8').splitlines() if x.strip()]
        recent = [x for x in m if x.get('detected_on') == session]
        L += ['', f"## Missed-winner audit ({len(m)} cases logged; {len(recent)} new today)"]
        L += [f"- {x['symbol']}: +{_md(x.get('excess_return_pct'))}% vs Nifty 500 since {x['move_start']} — {x['diagnosis']}" for x in recent[:10]]
    L += ['', '## Cash', f"Your confirmed cash ₹{cap['cash_inr']:,.0f} · confirmed holdings: {', '.join(cap['holdings']) or 'none'} · "
          'starter ₹2,500, build +₹3,000, core to ₹10,000; at most 4 open starters and 2 new a month.']
    if rows:
        b = rows[0]; r = b['r']
        L += ['', '## Final output', f"BEST CURRENT OPPORTUNITY: {b['symbol']}", f"CONFIRMATION / DISCOVERY: {b['conf']} / {_md(b['disc'])}",
              f"STATE: {b['state']}", f"EXPECTED VALUE (2y, probability-weighted): {_md(r.get('ev_2y_pct'))}% · bear case {_md(r.get('bear_downside_pct'))}%",
              f"WHY: {r['thesis']}"]
        for k in ('bear', 'base', 'bull'):
            sc = r['scenarios'].get(k, {})
            L.append(f"{k.upper()} CASE ({_md(sc.get('probability'))}): price {sc.get('price')} ({sc.get('multiple')}×) — {sc.get('assumptions', '')}")
        for k in ('2x', '3x', '5x', '10x'): L.append(f"{k.upper()} PLAUSIBLE? {r['plausible'].get(k, 'unknown')}")
        L += [f"BIGGEST THESIS RISK: {r.get('biggest_risk')}", f"NEXT DATAPOINT: {r.get('next_datapoint')}", f"CONFIDENCE: {r.get('confidence')}"]
    (INF/'report.md').write_text('\n'.join(L)+'\n', encoding='utf-8')


def queue(session, limit=5):
    """Who needs Stage 3 now: fast-lane tickets first, then finalists whose evidence changed."""
    stage2 = pd.read_csv(INF/'stage2.csv')
    from scanner.data import announcements
    news, _ = announcements(session, days=180)
    filings = {}
    for a in news:
        if a.get('desc') in ('Outcome of Board Meeting', 'Investor Presentation', 'Bagging/Receiving of orders/contracts',
                             'Commencement of commercial production/operations', 'Capacity addition', 'Credit Rating- Revision', 'Preferential issue'):
            filings.setdefault(a['symbol'], []).append(a)
    fast = stage2['fast_lane'] if 'fast_lane' in stage2 else pd.Series(False, index=stage2.index)
    cands = stage2[stage2['finalist'] | fast].assign(_fl=fast).sort_values(['_fl', 'stage2_score'], ascending=False)
    out = []
    for r in cands.to_dict('records'):
        rec = record(r['symbol'])
        why = ('fast lane: '+str(r.get('source'))) if r.get('_fl') and not rec else due(r, rec, session, filings)
        if why:
            out.append({'symbol': r['symbol'], 'trigger': why, 'dossier': f"runs/inflection/dossiers/{r['symbol']}.md",
                        'price': r['close'], 'discovery_d': r.get('discovery_score'), 'fast_lane': bool(r.get('_fl')),
                        'stage2_score': r['stage2_score']})
    out = out[:limit]
    (INF/'stage3_queue.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    return out, stage2


def ingest(symbol, result, session, price=None, discovery_d=None, fast_lane=False, model='Claude Code session',
           stage2_score=None, trigger='queue'):
    """Validate a Stage 3 result, append it to the thesis DB, and apply the state gate."""
    from underwriter import state as ST
    for key in ('score', 'status', 'thesis', 'scenarios', 'kill_conditions', 'sources', 'ev_2y_pct', 'bear_downside_pct'):
        if key not in result: raise ValueError(f'Stage 3 result missing {key}')
    probs = [v.get('probability') for v in result['scenarios'].values() if isinstance(v, dict)]
    if probs and all(p is not None for p in probs) and abs(sum(probs)-1) > 0.05:
        raise ValueError('Scenario probabilities must sum to 1')
    DB.mkdir(parents=True, exist_ok=True)
    rec = record(symbol) or {'symbol': symbol, 'discovered': session, 'discovery_price': price, 'reviews': []}
    rec['reviews'].append({'date': session, 'trigger': trigger, 'stage2_score': stage2_score, 'price': price, 'model': model,
                           'reviewed_at': datetime.now(timezone.utc).isoformat(), 'result': result})
    (DB/f'{symbol}.json').write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding='utf-8')
    pos = ST.load()
    new, inr, reason = ST.apply(symbol, result, pos, session, price, discovery_d, fast_lane)
    ST.save(pos)
    return new, inr, reason


def run(session, limit=None):
    """Daily: credit cash, build the Stage 3 queue, underwrite via API only if a key exists, rebuild the report."""
    DB.mkdir(parents=True, exist_ok=True)
    cap = capital(session)
    q, stage2 = queue(session)
    status = {'session': session, 'queue': q, 'reviewed': [], 'errors': [],
              'mode': 'Claude Code routine (subscription) unless ANTHROPIC_API_KEY is set'}
    limit = limit if limit is not None else int(os.getenv('UNDERWRITER_MAX', '3'))
    if q[:limit] and os.getenv('ANTHROPIC_API_KEY'):
        import anthropic
        client = anthropic.Anthropic()
        context = {'available_cash_inr': cap['cash_inr'], 'confirmed_holdings': cap['holdings']}
        for item in q[:limit]:
            sym = item['symbol']; rec = record(sym)
            try:
                dossier = (ROOT/item['dossier']).read_text(encoding='utf-8')
                result, text, usage = underwrite(client, sym, dossier, rec['reviews'][-1]['result'] if rec else None, context)
                new, inr, reason = ingest(sym, result, session, item['price'], item['discovery_d'], item['fast_lane'], MODEL,
                                          item['stage2_score'], item['trigger'])
                status['reviewed'].append({'symbol': sym, 'state': new, 'inr': inr, 'reason': reason, 'usage': usage})
            except Exception as exc:
                status['errors'].append(f'{sym}: {type(exc).__name__}: {exc}')
    report(session, stage2, cap)
    (INF/'underwriter_status.json').write_text(json.dumps(status, indent=1, default=str), encoding='utf-8')
    return status


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--session', required=True); p.add_argument('--limit', type=int)
    p.add_argument('--ingest', help='SYMBOL=path/to/result.json written by a Claude Code session')
    a = p.parse_args()
    if a.ingest:
        sym, path = a.ingest.split('=', 1)
        qp = INF/'stage3_queue.json'
        q = {x['symbol']: x for x in json.loads(qp.read_text(encoding='utf-8'))} if qp.exists() else {}
        item = q.get(sym, {})
        print(ingest(sym, json.loads(Path(path).read_text(encoding='utf-8')), a.session, item.get('price'), item.get('discovery_d'),
                     item.get('fast_lane', False), 'Claude Code session', item.get('stage2_score'), item.get('trigger', 'manual')))
        report(a.session, pd.read_csv(INF/'stage2.csv'), capital(a.session))
        return
    print(json.dumps(run(a.session, a.limit), indent=1, default=str))


if __name__ == '__main__':
    main()
