"""Daily Stages 1-2: scan Nifty Total Market (~750 stocks), funnel to ~10 dossiers.

    python -m scanner.run --session 2026-09-30
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scanner import data as D, score as S, stage2 as F

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'runs'/'inflection'


def run(session, refresh_universe=True):
    OUT.mkdir(parents=True, exist_ok=True)
    status = {'session': session, 'started_at': datetime.now(timezone.utc).isoformat(), 'warnings': []}
    if refresh_universe:
        try: D.refresh_universe()
        except Exception as exc: status['warnings'].append(f'Universe refresh failed, using saved list: {exc}')
    uni = D.universe()
    symbols = list(uni['symbol'])
    frames, perr = D.prices([s+'.NS' for s in symbols], session)
    fresh = {k[:-3]: v for k, v in frames.items() if str(v.index[-1].date()) == session}
    if len(fresh) < 0.8*len(symbols):
        raise RuntimeError(f'Only {len(fresh)} of {len(symbols)} symbols have {session} prices')
    fund, ferr = D.fundamentals([s+'.NS' for s in symbols])
    fund = {k[:-3]: v for k, v in fund.items()}
    news, nerr = D.announcements(session)
    news_ok = len(nerr) < 5 and len(news) > 0
    stage1 = S.scan(uni, fresh, fund, news, news_ok, as_of=session)
    stage1.to_csv(OUT/'stage1.csv', index=False)
    pool, finalists, _ = F.funnel(stage1, news if news_ok else [], session)
    with (OUT/'funnel_history.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'date': session, 'stage2_top10': list(finalists['symbol']),
                            'scores': dict(zip(finalists['symbol'], finalists['stage2_score']))}, sort_keys=True)+'\n')
    status.update(symbols=len(symbols), priced=len(fresh), fundamentals_ok=int(stage1['fundamentals_ok'].sum()),
                  vetoed=int((stage1['veto'].fillna('') != '').sum()), stage2_pool=len(pool),
                  finalists=list(finalists['symbol']), announcements=len(news), news_ok=news_ok,
                  price_errors=len(perr), fundamental_errors=len(ferr), announcement_errors=nerr[:5],
                  ended_at=datetime.now(timezone.utc).isoformat())
    (OUT/'status.json').write_text(json.dumps(status, indent=1), encoding='utf-8')
    return status, stage1, pool


def main():
    p = argparse.ArgumentParser(); p.add_argument('--session', required=True)
    status, stage1, pool = run(p.parse_args().session)
    print(json.dumps(status, indent=1))
    cols = ['symbol', 'industry', 'stage1_score', 'stage2_score', 'industry_score', 'rev_yoy', 'ebitda_yoy', 'pat_yoy', 'cfo_to_pat', 'pe', 'market_cap_cr']
    print(pool.head(20)[cols].to_string())


if __name__ == '__main__':
    main()
