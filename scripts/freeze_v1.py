"""One-time archive from a pinned Git revision; refuses to overwrite any freeze."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = '75dd97e0cca9a89f7f2c1dec6706607cab388e40'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    dest = ROOT / 'strategies/dhruva_v1'
    manifest_path = dest / 'strategy_manifest.yaml'
    if manifest_path.exists() or (dest / 'snapshot').exists():
        raise SystemExit('Freeze already exists. Never overwrite it; create a new strategy version.')
    paths = git('ls-tree', '-r', '--name-only', REVISION).decode().splitlines()
    archived = [p for p in paths if p.startswith(('qlab/', 'scripts/', 'runs/')) or p in
                ('config.json', 'data/nifty500.txt', 'data/nifty100.txt', 'data/nifty500_industry.json',
                 'data/nse_names.json', 'reports/dashboard.html', 'streamlit_app.py', 'README.md',
                 'AGENTS.md', 'requirements.txt', '.github/workflows/daily.yml')]
    hashes = {}
    for p in archived:
        blob = git('show', f'{REVISION}:{p}')
        out = dest / 'snapshot' / p
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        hashes[p] = hashlib.sha256(blob).hexdigest()
    cfg = json.loads((dest / 'snapshot/config.json').read_text(encoding='utf-8'))
    guarded = [p for p in hashes if p.startswith('qlab/') and Path(p).name not in
               {'orchestrator.py', 'report.py', 'narrator.py', 'notify.py', 'news.py', 'advisor.py', 'learn.py'}]
    guarded += ['config.json', 'data/nifty500.txt', 'data/nifty500_industry.json']
    manifest = {
        'strategy_id': 'dhruva_momentum', 'strategy_version': '1.0', 'name': 'Dhruva v1.0',
        'frozen_at': datetime.now(timezone.utc).isoformat(), 'source_git_commit': REVISION,
        'execution_mode': 'PAPER', 'live_start_date_recorded': '2026-09-16',
        'timestamp_quality': 'Legacy import: original per-decision UTC generation timestamps unavailable; do not infer them.',
        'universe': {'file': 'data/nifty500.txt', 'membership': 'current constituents, not point-in-time',
                     'count': len((dest / 'snapshot/data/nifty500.txt').read_text().splitlines()),
                     'additional_data': list(cfg['defensive_basket'])},
        'benchmark': {'symbol': '^NSEI', 'type': 'Nifty 50 price index, excludes dividends',
                      'choice': 'existing predetermined benchmark; live comparison absent in original'},
        'factors': {'momentum12_1': '(adjclose.shift(21)/adjclose.shift(252)-1)*100',
                    'momentum6_1': '(adjclose.shift(21)/adjclose.shift(126)-1)*100',
                    'score': '(0.7*momentum12_1+0.3*momentum6_1)/vol20',
                    'volatility': '20-session annualized adjusted-close return standard deviation'},
        'signals': 'Positive raw momentum and adjclose > own 200-session average; benchmark trend gates new stocks.',
        'ranking': 'Descending (score, symbol); up to 15; 60-session median turnover >= INR50m; at most 4 per sector.',
        'entry': 'At review schedule new leaders; value=(1/15)*clip(0.30/vol20,0.4,1.8)*equity_weight*NAV; next available open +12bps.',
        'exit': 'Rank/regime exits at review; near-365-day winners deferred within 35 days; 4 raw ATR fixed stop; breaker overrides deferral.',
        'rebalance': {'sessions': 63, 'first_step': True, 'interim_trigger': 'breaker with stock holdings'},
        'portfolio': {'books': cfg['books'], 'allocation': cfg['allocation'], 'basket': cfg['defensive_basket'],
                      'configured_max_stock_weight': 0.12, 'actual_live_cap_enforced': False,
                      'basket_trade_threshold': '6% of current or target value', 'fractional_shares': False},
        'risk': cfg['risk'], 'cost_assumptions': cfg['costs'], 'slippage_bps': cfg['slippage_bps'],
        'tax_assumptions': cfg['tax'], 'tax_accounting': 'Accrued per book only; NOT deducted/reserved in original NAV.',
        'settlement': 'T+1 weekday labels only in v1; proceeds immediately spendable; no holiday calendar.',
        'starting_capital_inr': 100000, 'starting_nav_index': 100,
        'data_source': 'Yahoo chart API daily adjusted OHLC; five-year range; recent three-month mutable merge.',
        'backtest': {'legacy_comparison_period': ['2022-09-30', '2026-09-16'],
                     'convention': 'same-close, pre-tax; not exact live execution; historical results kept as legacy evidence',
                     'challenge_study': 'separate audited simulator; not this frozen version'},
        'limitations': ['centered cleaner changes past with future data', 'raw ATR vs adjusted fills',
                       'optimistic gap stops', 'tax omitted from NAV and duplicated exemptions',
                       'unsettled sale cash reused', 'missed-day recovery skips sessions',
                       'old settled orders pruned', 'aggressive book may rank diversifiers',
                       'intraday manual run recorded unfinished Sep17 bar', 'stale input and mixed quote/NAV dates',
                       'current constituents and revised adjusted prices', 'only two original recorded live dates'],
        'version_policy': 'Changes to signals, universe, sizing, execution, cost, tax or accounting start a new prospective track. No rewritten original evidence.',
        'snapshot_hash_algorithm': 'sha256; exact Git blob bytes', 'snapshot_files': hashes,
        'active_guard_files': guarded,
        'cache_provenance': {'git_commit': REVISION, 'path': 'data/cache/',
                             'note': 'Original input bytes retrievable by Git commit; not copied twice.'},
    }
    # JSON is a YAML 1.2 subset and avoids a runtime YAML dependency.
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    (dest / 'manifest.sha256').write_text(hashlib.sha256(manifest_path.read_bytes()).hexdigest()+'\n', encoding='ascii')
    print(f'Frozen {len(hashes)} files at {REVISION}; {len(guarded)} active guard paths.')


if __name__ == '__main__':
    main()
