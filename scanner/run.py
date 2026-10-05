"""Daily Stages 1-2 over all NSE main-board and trade-for-trade equities (~2,500).

    python -m scanner.run --session 2026-10-05
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scanner import data as D, score as S, stage2 as F, events as EV, discovery as DS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'runs'/'inflection'
MIN_TURNOVER_CR = 1.0
MIN_MCAP_CR = 500


def usd_inr():
    from dhruva.marketdata import yahoo_close
    try:
        return float(yahoo_close('INR=X').iloc[-1])
    except Exception:
        return 88.0  # fallback only for order-value conversion; logged in status


def run(session, refresh_universe=True):
    OUT.mkdir(parents=True, exist_ok=True)
    status = {'session': session, 'started_at': datetime.now(timezone.utc).isoformat(), 'warnings': []}
    if refresh_universe:
        try: D.refresh_universe()
        except Exception as exc: status['warnings'].append(f'Universe refresh failed, using saved list: {exc}')
    uni = D.universe()
    symbols = list(uni['symbol'])
    frames, perr = D.prices([s+'.NS' for s in symbols], session)
    frames = {k[:-3]: v for k, v in frames.items()}
    fresh = {s: f for s, f in frames.items() if str(f.index[-1].date()) == session}
    if len(fresh) < 0.7*len(symbols):
        raise RuntimeError(f'Only {len(fresh)} of {len(symbols)} symbols have {session} prices')
    liquid = [s for s, f in fresh.items() if float((f['close']*f['volume']).iloc[-20:].mean())/1e7 >= MIN_TURNOVER_CR]
    fund, ferr = D.fundamentals([s+'.NS' for s in liquid])
    fund = {k[:-3]: v for k, v in fund.items()}
    news, nerr = D.announcements(session, days=180)
    news_ok = len(nerr) < 5 and len(news) > 0
    rate = usd_inr()
    events = EV.evaluate(news if news_ok else [], fund, fresh, rate, universe=set(liquid))
    hot = EV.surveillance_join(news, events)
    new_signals = EV.log_signals(events, session)
    if len(events): events.to_csv(OUT/'events.csv', index=False)
    stage1 = S.scan(uni[uni['symbol'].isin(liquid)], fresh, fund, news, news_ok, as_of=session)
    disc = DS.score_all(list(stage1['symbol']), fund, events, session)
    stage1 = stage1.merge(disc, on='symbol', how='left')
    stage1['confirmation_score'] = stage1['stage1_score']
    stage1['surveillance_with_event'] = stage1['symbol'].isin(hot)
    stage1['series'] = stage1['symbol'].map(uni.set_index('symbol')['series']) if 'series' in uni else 'EQ'
    stage1.to_csv(OUT/'stage1.csv', index=False)
    pool, finalists, _ = F.funnel(stage1, news if news_ok else [], session, events, min_turnover_cr=MIN_TURNOVER_CR, min_mcap_cr=MIN_MCAP_CR)
    with (OUT/'funnel_history.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'date': session, 'stage2_top10': list(finalists['symbol']),
                            'fast_lane': list(pool.loc[pool['fast_lane'], 'symbol']),
                            'scores': dict(zip(finalists['symbol'], finalists['stage2_score']))}, sort_keys=True)+'\n')
    status.update(universe=len(symbols), priced=len(fresh), liquid=len(liquid),
                  eligible=int(((stage1['turnover_cr'] >= MIN_TURNOVER_CR) & (stage1['market_cap_cr'].fillna(0) >= MIN_MCAP_CR)).sum()),
                  fundamentals_ok=int(stage1['fundamentals_ok'].sum()), vetoed=int((stage1['veto'].fillna('') != '').sum()),
                  material_events=int(events['material'].sum()) if len(events) else 0, new_signals=len(new_signals),
                  fast_lane=list(pool.loc[pool['fast_lane'], 'symbol']), finalists=list(finalists['symbol']),
                  announcements=len(news), news_ok=news_ok, usd_inr=rate, price_errors=len(perr),
                  fundamental_errors=len(ferr), announcement_errors=nerr[:5], ended_at=datetime.now(timezone.utc).isoformat())
    (OUT/'status.json').write_text(json.dumps(status, indent=1), encoding='utf-8')
    return status, stage1, pool


def main():
    p = argparse.ArgumentParser(); p.add_argument('--session', required=True)
    status, stage1, pool = run(p.parse_args().session)
    print(json.dumps(status, indent=1))
    cols = ['symbol', 'industry', 'source', 'discovery_score', 'stage1_score', 'order_intensity_180d', 'capacity_pct_365d',
            'promoter_pct_mcap_365d', 'rev_yoy', 'ebitda_yoy', 'market_cap_cr']
    print(pool.head(25)[[c for c in cols if c in pool]].to_string())


if __name__ == '__main__':
    main()
