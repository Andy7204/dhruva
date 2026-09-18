"""Quant Lab — an INR paper-trading research system.

EDUCATIONAL RESEARCH ONLY. Nothing here is investment advice, and no real
orders are ever placed. Backtest / paper results systematically overstate what
live trading would achieve.
"""
__version__ = "0.1.0"

# Windows consoles default to cp1252 and cannot print the rupee sign; force UTF-8.
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

