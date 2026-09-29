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


def report(session, stage2, cap):
    rows = []
    for path in sorted(DB.glob('*.json')):
        rec = json.loads(path.read_text(encoding='utf-8')); r = rec['reviews'][-1]; prev = rec['reviews'][-2] if len(rec['reviews']) > 1 else None
        rows.append({'symbol': rec['symbol'], 'score': r['result']['score']['total'], 'prev': prev['result']['score']['total'] if prev else None,
                     'status': r['result']['status'], 'action': r['result']['action'], 'date': r['date'], 'r': r['result'],
                     'discovered': rec['discovered'], 'discovery_price': rec['discovery_price']})
    rows.sort(key=lambda x: -x['score'])
    L = [f'# Dhruva inflection report — {session}', '', 'Paper research, not investment advice. Holdings change only after the owner confirms a trade.', '']
    changed = [x for x in rows if x['date'] == session]
    L += ['## Material changes', '| Company | Previous | New | Status | Action | Change |', '|---|---:|---:|---|---|---|']
    L += [f"| {x['symbol']} | {x['prev'] if x['prev'] is not None else '—'} | {x['score']} | {x['status']} | {x['action']} | {x['r'].get('material_change', '')} |" for x in changed] or ['| none today | | | | | |']
    L += ['', '## Sandisk radar (latest underwriting, by score)', '| Company | Score | Status | Action | Last review | Discovered at |', '|---|---:|---|---|---|---|']
    L += [f"| {x['symbol']} | {x['score']} | {x['status']} | {x['action']} | {x['date']} | ₹{x['discovery_price']} on {x['discovered']} |" for x in rows]
    L += ['', '## Stage 2 finalists today (quantitative, not yet underwritten unless listed above)']
    L += [f"- {r.symbol} ({r.industry}): Stage 2 {r.stage2_score}, Stage 1 {r.stage1_score}" for r in stage2[stage2['finalist']].itertuples()]
    L += ['', '## Action engine', f"Available cash ₹{cap['cash_inr']:,.0f} · confirmed holdings: {', '.join(cap['holdings']) or 'none'}"]
    buys = [x for x in changed if x['r']['action'] in ('BUY', 'ADD') and x['score'] >= 80]
    if buys:
        for x in buys: L.append(f"- {x['r']['action']} {x['symbol']}: up to ₹{min(x['r'].get('capital_to_deploy_inr', 0), cap['cash_inr']):,.0f} (paper recommendation; not executed)")
    else:
        L.append('- NO ACTION. Cash is a legitimate position.')
    if rows:
        b = rows[0]; r = b['r']
        L += ['', '## Final output', f"BEST CURRENT OPPORTUNITY: {b['symbol']}", f"CURRENT SCORE: {b['score']}", f"BEST ACTION: {r['action']}",
              f"CAPITAL TO DEPLOY NOW: ₹{r.get('capital_to_deploy_inr', 0) if b in buys else 0:,.0f}", f"WHY: {r['thesis']}"]
        for k in ('bear', 'base', 'bull'):
            sc = r['scenarios'].get(k, {}); L.append(f"{k.upper()} CASE: price {sc.get('price')} ({sc.get('multiple')}×, {sc.get('cagr_pct')}% CAGR) — {sc.get('assumptions', '')}")
        for k in ('2x', '3x', '5x', '10x'): L.append(f"{k.upper()} PLAUSIBLE? {r['plausible'].get(k, 'unknown')}")
        L += [f"BIGGEST THESIS RISK: {r.get('biggest_risk')}", f"NEXT DATAPOINT: {r.get('next_datapoint')}", f"CONFIDENCE: {r.get('confidence')}"]
    (INF/'report.md').write_text('\n'.join(L)+'\n', encoding='utf-8')


def run(session, limit=None):
    DB.mkdir(parents=True, exist_ok=True)
    stage2 = pd.read_csv(INF/'stage2.csv')
    cap = capital(session)
    finalists = stage2[stage2['finalist']]
    from scanner.data import announcements
    news, _ = announcements(session)
    filings = {}
    for a in news:
        if a.get('desc') in ('Outcome of Board Meeting', 'Investor Presentation', 'Bagging/Receiving of orders/contracts',
                             'Commencement of commercial production/operations', 'Credit Rating- Revision'):
            filings.setdefault(a['symbol'], []).append(a)
    queue = [(r, why) for r in finalists.to_dict('records') if (why := due(r, record(r['symbol']), session, filings))]
    limit = limit if limit is not None else int(os.getenv('UNDERWRITER_MAX', '3'))
    status = {'session': session, 'queued': [(r['symbol'], why) for r, why in queue], 'reviewed': [], 'errors': []}
    if queue[:limit] and not (os.getenv('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_AUTH_TOKEN')):
        status['errors'].append('No Anthropic credential; Stage 3 skipped. Add the ANTHROPIC_API_KEY repository secret.')
        queue = []
    if queue[:limit]:
        import anthropic
        client = anthropic.Anthropic()
        context = {'available_cash_inr': cap['cash_inr'], 'confirmed_holdings': cap['holdings'],
                   'priority_list': [{'symbol': p.stem, 'score': json.loads(p.read_text(encoding='utf-8'))['reviews'][-1]['result']['score']['total']}
                                     for p in DB.glob('*.json')]}
        for row, why in queue[:limit]:
            sym = row['symbol']; rec = record(sym)
            try:
                dossier = (INF/'dossiers'/f'{sym}.md').read_text(encoding='utf-8')
                result, text, usage = underwrite(client, sym, dossier, rec['reviews'][-1]['result'] if rec else None, context)
                rec = rec or {'symbol': sym, 'discovered': session, 'discovery_price': row['close'], 'reviews': []}
                rec['reviews'].append({'date': session, 'trigger': why, 'stage2_score': row['stage2_score'], 'price': row['close'],
                                       'model': MODEL, 'usage': usage, 'reviewed_at': datetime.now(timezone.utc).isoformat(),
                                       'result': result})
                (DB/f'{sym}.json').write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding='utf-8')
                (INF/'transcripts').mkdir(exist_ok=True)
                (INF/'transcripts'/f'{sym}_{session}.md').write_text(text, encoding='utf-8')
                status['reviewed'].append({'symbol': sym, 'score': result['score']['total'], 'action': result['action'], 'usage': usage})
            except Exception as exc:
                status['errors'].append(f'{sym}: {type(exc).__name__}: {exc}')
    report(session, stage2, cap)
    (INF/'underwriter_status.json').write_text(json.dumps(status, indent=1), encoding='utf-8')
    return status


def main():
    p = argparse.ArgumentParser(); p.add_argument('--session', required=True); p.add_argument('--limit', type=int)
    a = p.parse_args()
    print(json.dumps(run(a.session, a.limit), indent=1))


if __name__ == '__main__':
    main()
