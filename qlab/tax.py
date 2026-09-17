"""Indian capital-gains tax on realised sales — approximate, post-Budget 2024.

  • Equity & equity ETFs (stocks, NIFTYBEES…): STCG 20% if held ≤12 months;
    LTCG 12.5% on gains above ₹1.25 lakh per financial year.
  • Non-equity (gold/silver ETFs, InvIT, liquid ETF): short-term taxed at your
    income-slab rate (default 30%); long-term (>12 months) at 12.5%.

Losses net against gains within the same bucket & financial year; tax is charged
only on the net positive. Rates/rules change and depend on YOUR slab — verify with
a CA. This models the drag so "what you keep" is honest, not a filing engine.
"""
from __future__ import annotations

from collections import defaultdict


def _fy(date_str: str) -> int:
    y, m, _ = (int(x) for x in date_str.split("-"))
    return y if m >= 4 else y - 1  # Indian FY starts 1 April


def is_equity(sym: str, cfg: dict) -> bool:
    non_eq = set((cfg.get("defensive_basket") or {}).keys())
    if cfg.get("defensive_asset"):
        non_eq.add(cfg["defensive_asset"])
    return sym not in non_eq  # plain stocks & equity ETFs are equity; the basket is not


def accrued_tax(sales: list[dict], cfg: dict):
    """sales: [{symbol, exit_date 'YYYY-MM-DD', holding_days, gain}]. → (total, breakdown)."""
    tx = cfg.get("tax", {})
    if not tx.get("enabled") or not sales:
        return 0.0, {}
    ltd = tx.get("long_term_days", 365)
    buckets: dict = defaultdict(lambda: defaultdict(float))
    for s in sales:
        eq = is_equity(s["symbol"], cfg)
        lng = s["holding_days"] > ltd
        key = ("eq_" if eq else "ne_") + ("ltcg" if lng else "stcg")
        buckets[_fy(s["exit_date"])][key] += s["gain"]
    total, detail = 0.0, defaultdict(float)
    for _, b in buckets.items():
        parts = {
            "equity STCG 20%": max(0.0, b.get("eq_stcg", 0)) * tx["equity_stcg_pct"],
            "equity LTCG 12.5%": max(0.0, b.get("eq_ltcg", 0) - tx["ltcg_exemption"]) * tx["equity_ltcg_pct"],
            "other short (slab)": max(0.0, b.get("ne_stcg", 0)) * tx["nonequity_short_pct"],
            "other LTCG 12.5%": max(0.0, b.get("ne_ltcg", 0)) * tx["nonequity_long_pct"],
        }
        for k, v in parts.items():
            total += v; detail[k] += v
    return round(total, 2), {k: round(v, 2) for k, v in detail.items() if v > 0.5}
