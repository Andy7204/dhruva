"""Explicit, bounded exchange calendar. Never silently extrapolate future years."""
from datetime import datetime, timedelta, time
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
IST = ZoneInfo('Asia/Kolkata')


def calendar_config():
    return json.loads((ROOT/'data/trading_calendar.json').read_text(encoding='utf-8'))


def is_session(day, cfg=None):
    cfg = cfg or calendar_config()
    if not cfg['valid_from'] <= day.isoformat() <= cfg['valid_through']:
        raise ValueError(f'Exchange calendar coverage unavailable for {day}; review official circulars')
    return day.weekday() < 5 and day.isoformat() not in cfg['holidays']


def expected_date(now=None, cfg=None):
    cfg = cfg or calendar_config()
    now = (now or datetime.now(IST)).astimezone(IST)
    day = now.date()
    # Daily vendor data has a buffer after the regular market close. Normal
    # published deadline is 18:30 IST; this boundary prevents intraday processing.
    if now.time() < time(16, 30): day -= timedelta(days=1)
    for _ in range(10):
        # Sept17 is the known preceding original session; not broad historic coverage.
        if day.isoformat() == '2026-09-17': return day.isoformat()
        if is_session(day, cfg): return day.isoformat()
        day -= timedelta(days=1)
    raise ValueError('No verified recent session')


def run_due(now=None, cfg=None):
    cfg = cfg or calendar_config()
    now = (now or datetime.now(IST)).astimezone(IST)
    if not is_session(now.date(), cfg): return False, 'NON_TRADING_DAY'
    if now.time() < time(16, 30): return False, 'BEFORE_COMPLETED_SESSION'
    return True, 'DUE'
