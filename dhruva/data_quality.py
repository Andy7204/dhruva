"""Past-only daily input contract. No silent stale-cache success."""
import pandas as pd

from dhruva.calendar import expected_date, is_session
from dhruva.ledger import atomic_write, canonical, utc_now
from qlab.data import OHLCV, clean_ohlc


class DataQualityError(ValueError):
    pass


def validate_inputs(raw, benchmark, cfg, states, root, *, expected=None):
    expected = expected or expected_date()
    cutoff = pd.Timestamp(expected)
    report = dict(generated_at=utc_now(), expected_date=expected, status='FAILED',
                  excluded={}, warnings=[], errors=[], symbols={},
                  convention='Adjusted-price research units; current constituents, not point-in-time membership')
    required = {s for st in states.values() for s in (st or {}).get('holdings', {})}
    valid = {}

    def check(symbol, frame, index=False):
        info = {}; report['symbols'][symbol] = info
        if frame is None or frame.empty: raise DataQualityError('missing/empty data')
        if frame.attrs.get('fetch_error'): raise DataQualityError('fetch failed: '+frame.attrs['fetch_error'])
        if not set(OHLCV) <= set(frame): raise DataQualityError('missing OHLCV columns')
        if not isinstance(frame.index,pd.DatetimeIndex) or frame.index.hasnans:
            raise DataQualityError('invalid date index')
        if frame.index.has_duplicates: raise DataQualityError('duplicate session dates')
        if frame.index.tz is not None: raise DataQualityError('unexpected timezone in daily session dates')
        # Exclude an in-progress bar explicitly; never call it a final daily input.
        usable = frame.loc[frame.index <= cutoff].sort_index()
        info['future_or_unfinished_rows_excluded'] = len(frame)-len(usable)
        if usable.empty or usable.index[-1] != cutoff:
            raise DataQualityError('stale/missing completed session '+expected)
        cleaned = clean_ohlc(usable)
        info['invalid_rows_removed'] = len(usable)-len(cleaned)
        if cleaned.empty or cleaned.index[-1] != cutoff:
            raise DataQualityError('latest OHLCV row invalid')
        if len(cleaned)<200: raise DataQualityError('insufficient trend history (<200 sessions)')
        if not index and cleaned['volume'].iloc[-1] <= 0:
            raise DataQualityError('zero latest trading volume')
        changes = cleaned['adjclose'].pct_change().abs()
        info['suspicious_adjusted_jumps'] = int((changes > .5).sum())
        factor = cleaned['adjclose']/cleaned['close']
        info['adjustment_factor_changes'] = int((factor.pct_change().abs()>.05).sum())
        if changes.iloc[-1] > .5:
            raise DataQualityError('latest adjusted price jump >50%; review corporate action')
        info.update(latest_date=expected, rows=len(cleaned))
        return cleaned

    try:
        bench = check(cfg['regime']['benchmark'],benchmark,index=True)
        for state in states.values():
            pt = (state or {}).get('processed_through')
            if pt:
                for day in pd.date_range(pd.Timestamp(pt)+pd.Timedelta(days=1),cutoff):
                    if is_session(day.date()) and day not in bench.index:
                        raise DataQualityError('missing recovery benchmark session '+str(day.date()))
    except (ValueError,TypeError,KeyError) as exc:
        report['errors'].append('BENCHMARK: '+str(exc)); bench=None
    for symbol in sorted(set(cfg['universe']) | required):
        try: valid[symbol]=check(symbol,raw.get(symbol))
        except (ValueError,TypeError,KeyError) as exc:
            report['excluded'][symbol]=str(exc)
            if symbol in required: report['errors'].append('HELD '+symbol+': '+str(exc))
    coverage = len(set(valid)&set(cfg['universe']))/max(1,len(set(cfg['universe'])))
    report['coverage']=coverage
    minimum = cfg.get('data',{}).get('minimum_coverage', .95)
    if coverage < minimum: report['errors'].append(f'Universe coverage {coverage:.1%} below {minimum:.1%}')
    if report['excluded']: report['warnings'].append('Excluded symbols are ineligible for orders; see per-symbol reasons')
    if any(i.get('invalid_rows_removed') or i.get('suspicious_adjusted_jumps') for i in report['symbols'].values()):
        report['warnings'].append('Historical anomalies flagged; rowwise cleaning is causal, corporate actions are not independently certified')
    if not report['errors']: report['status']='VALID_WITH_EXCLUSIONS' if report['excluded'] else 'VALID'
    atomic_write(root/'runs/data_quality.json',canonical(report)+b'\n')
    if report['errors']: raise DataQualityError('; '.join(report['errors']))
    return valid, bench, report
