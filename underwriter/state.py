"""Position state machine and rule gate (docs/ARCHITECTURE_V3.md section G).

Stage 3 proposes; this gate decides. Rules are deterministic so the same
evidence always gives the same state, and every transition is logged with the
evidence that justified it. A paper "model portfolio" follows the gate's
recommendations at the next close so the system's calls can be measured;
the owner's real holdings (runs/inflection/capital.json) change only on
confirmed trades.
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INF = ROOT/'runs'/'inflection'
STATES = ('DISCOVER', 'RESEARCH', 'STARTER', 'BUILD', 'CORE', 'HOLD', 'TRIM', 'EXIT')
TARGET, STARTER_INR, BUILD_INR = 10_000, 2_500, 3_000
RULES = {'starter_discovery': 70, 'starter_ev': 30, 'starter_downside': -35, 'build_ev': 25, 'core_confirmation': 75,
         'core_ev': 20, 'core_cfo_pat': 0.7, 'hold_ev': 20, 'research_discovery': 60, 'max_open_starters': 4,
         'max_new_starters_month': 2, 'time_stop_days': 182}


def load():
    path = INF/'positions.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def save(pos):
    (INF/'positions.json').write_text(json.dumps(pos, indent=1, ensure_ascii=False), encoding='utf-8')


def discovery_total(discovery_d, discovery_j):
    """Discovery = 60% deterministic + 40% Claude judgement."""
    if discovery_j is None: return discovery_d
    return round(0.6*(discovery_d or 0)+0.4*discovery_j, 1)


def gate(symbol, proposal, pos, session, price, discovery_d=None, fast_lane=False):
    """Return (new_state, action_inr, reason). Mutates nothing."""
    cur = pos.get(symbol, {}); state = cur.get('state', 'DISCOVER')
    disc = discovery_total(discovery_d, proposal.get('discovery_judgement'))
    conf = proposal.get('confirmation_score') or (proposal.get('score') or {}).get('total')
    ev, down = proposal.get('ev_2y_pct'), proposal.get('bear_downside_pct')
    risk = proposal.get('risk') or {}
    high_risk = any(str(v).upper() == 'HIGH' for k, v in risk.items() if k in ('governance', 'balance_sheet'))
    kill = proposal.get('kill_condition_triggered')
    new_type = proposal.get('new_evidence_type')
    seen_types = {e.get('type') for e in cur.get('evidence', [])}
    invested = sum(e['inr'] for e in cur.get('entries', []))
    bull = proposal.get('bull_value_per_share')
    open_starters = sum(1 for p in pos.values() if p.get('state') == 'STARTER')
    month = session[:7]
    new_this_month = sum(1 for p in pos.values() for e in p.get('entries', []) if e['stage'] == 'STARTER' and e['date'][:7] == month)

    if kill or high_risk:
        return ('EXIT' if invested else 'RESEARCH' if disc and disc >= RULES['research_discovery'] else 'DISCOVER',
                0, f"{'kill condition: '+str(kill) if kill else 'governance/balance-sheet risk HIGH'}")
    if invested and ev is not None and ev < 0:
        if bull and price and price > bull: return 'TRIM', 0, 'price above bull-case value and expected value negative'
        if proposal.get('confirmation_falling'): return 'EXIT', 0, 'expected value negative and confirmation falling'
        return 'TRIM', 0, 'expected value negative at current price'
    if invested and bull and price and price > bull:
        return 'TRIM', 0, 'price above bull-case value'
    if state == 'STARTER' and cur.get('since') and (date.fromisoformat(session)-date.fromisoformat(cur['since'])).days > RULES['time_stop_days'] \
            and (not new_type or new_type in seen_types):
        return 'EXIT', 0, 'time-stop: no independent confirmation within two quarters'
    if state in ('STARTER', 'BUILD', 'CORE', 'HOLD'):
        fresh = new_type and new_type not in seen_types
        if (state in ('STARTER', 'BUILD') and conf and conf >= RULES['core_confirmation'] and ev is not None and ev >= RULES['core_ev']
                and (proposal.get('cfo_to_pat_value') or 0) >= RULES['core_cfo_pat'] and proposal.get('reported_earnings_confirm')):
            return 'CORE', max(0, TARGET-invested), 'earnings and cash flow confirm; expected value still attractive'
        if state == 'STARTER' and fresh and ev is not None and ev >= RULES['build_ev']:
            return 'BUILD', BUILD_INR, f'new independent evidence ({new_type}); expected value {ev:.0f}%'
        if ev is not None and ev < RULES['hold_ev']:
            return 'HOLD', 0, f'thesis intact but expected value {ev:.0f}% below add threshold'
        return state, 0, 'no new independent evidence; no add on price alone'
    # not invested yet
    if (disc and disc >= RULES['starter_discovery'] and proposal.get('hard_numeric_fact') and ev is not None and ev >= RULES['starter_ev']
            and down is not None and down >= RULES['starter_downside']):
        if open_starters >= RULES['max_open_starters']: return 'RESEARCH', 0, 'starter criteria met but 4 starters already open'
        if new_this_month >= RULES['max_new_starters_month']: return 'RESEARCH', 0, 'starter criteria met but 2 new starters this month already'
        return 'STARTER', STARTER_INR, f"discovery {disc}, hard fact: {proposal.get('hard_numeric_fact_text', 'yes')}, EV {ev:.0f}%, downside {down:.0f}%"
    if fast_lane or (disc and disc >= RULES['research_discovery']):
        return 'RESEARCH', 0, 'fast-lane event or discovery >= 60'
    return 'DISCOVER', 0, 'below research threshold'


def apply(symbol, proposal, pos, session, price, discovery_d=None, fast_lane=False):
    """Run the gate, update positions, log the transition and the paper model trade."""
    new, inr, reason = gate(symbol, proposal, pos, session, price, discovery_d, fast_lane)
    cur = pos.setdefault(symbol, {'state': 'DISCOVER', 'evidence': [], 'entries': []})
    old = cur['state']
    if proposal.get('new_evidence_type'):
        cur['evidence'].append({'date': session, 'type': proposal['new_evidence_type'], 'text': proposal.get('hard_numeric_fact_text', '')})
    if inr:
        stage = new if new in ('STARTER', 'BUILD', 'CORE') else old
        cur['entries'].append({'date': session, 'price': price, 'inr': inr, 'stage': stage})
    if new != old: cur['since'] = session
    cur['state'] = new; cur['last_reason'] = reason; cur['last_review'] = session
    cur['discovery'] = discovery_total(discovery_d, proposal.get('discovery_judgement'))
    cur['confirmation'] = proposal.get('confirmation_score') or (proposal.get('score') or {}).get('total')
    cur['ev_2y_pct'] = proposal.get('ev_2y_pct')
    with (INF/'transitions.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'date': session, 'symbol': symbol, 'from': old, 'to': new, 'inr': inr, 'price': price,
                            'reason': reason}, sort_keys=True)+'\n')
    if inr or new in ('TRIM', 'EXIT') and old in ('STARTER', 'BUILD', 'CORE', 'HOLD'):
        with (INF/'model_trades.jsonl').open('a', encoding='utf-8') as f:
            side = 'BUY' if inr else ('SELL_ALL' if new == 'EXIT' else 'SELL_40PCT')
            f.write(json.dumps({'decided': session, 'symbol': symbol, 'side': side, 'inr': inr,
                                'decision_price': price, 'fill': 'next session close (paper)'}, sort_keys=True)+'\n')
    return new, inr, reason
