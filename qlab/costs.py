"""Groww transaction-cost model for Indian equities.

Models the full stack of charges on a delivery/intraday order:
brokerage + STT + exchange txn + SEBI + stamp duty + GST + DP charge.

Rates live in config.json -> "costs" and are approximate as of 2026.
VERIFY against Groww's live brokerage calculator and update the config; these
change with regulation. This is a research approximation, not a billing engine.
"""
from __future__ import annotations


def exchange_of(symbol: str) -> str:
    if symbol.upper().endswith(".BO"):
        return "BSE"
    return "NSE"  # .NS and index ETFs default to NSE


def order_charges(value: float, side: str, product: str, exchange: str,
                  costs: dict) -> dict:
    """Charges for a single BUY or SELL order. `value` = qty * price (INR)."""
    side = side.lower()
    product = product.lower()
    value = float(abs(value))

    brokerage = min(costs["brokerage_cap"], costs["brokerage_pct"] * value)
    brokerage = max(costs["brokerage_floor"], brokerage) if value > 0 else 0.0

    if product == "delivery":
        stt = costs["stt_delivery_buy"] * value if side == "buy" else costs["stt_delivery_sell"] * value
        stamp = costs["stamp_duty_buy_delivery"] * value if side == "buy" else 0.0
        dp = costs["dp_charge_sell_delivery"] if side == "sell" else 0.0
    else:  # intraday
        stt = 0.0 if side == "buy" else costs["stt_intraday_sell"] * value
        stamp = costs["stamp_duty_buy_intraday"] * value if side == "buy" else 0.0
        dp = 0.0

    exch_rate = costs["exch_txn_bse"] if exchange == "BSE" else costs["exch_txn_nse"]
    exch_txn = exch_rate * value
    sebi = costs["sebi_charges"] * value
    gst = costs["gst_pct"] * (brokerage + exch_txn + sebi)
    total = brokerage + stt + exch_txn + sebi + stamp + gst + dp
    return {
        "value": value, "brokerage": brokerage, "stt": stt, "exch_txn": exch_txn,
        "sebi": sebi, "stamp": stamp, "gst": gst, "dp": dp, "total": total,
    }


def order_cost(value: float, side: str, symbol: str, product: str,
               costs: dict) -> float:
    return order_charges(value, side, product, exchange_of(symbol), costs)["total"]


def round_trip(buy_value: float, sell_value: float, symbol: str,
               product: str, costs: dict) -> dict:
    exch = exchange_of(symbol)
    b = order_charges(buy_value, "buy", product, exch, costs)
    s = order_charges(sell_value, "sell", product, exch, costs)
    total = b["total"] + s["total"]
    gross = sell_value - buy_value
    return {
        "buy": b, "sell": s, "total_charges": total,
        "gross_pnl": gross, "net_pnl": gross - total,
        "cost_pct_of_buy": (total / buy_value * 100) if buy_value else 0.0,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).resolve().parents[1] / "config.json").read_text())
    C = cfg["costs"]
    for v, sym in [(6000, "RELIANCE.NS"), (20000, "TCS.NS"), (6000, "HDFCBANK.BO")]:
        rt = round_trip(v, v * 1.03, sym, "delivery", C)
        print(f"{sym} buy≈₹{v} sell +3%:  charges ₹{rt['total_charges']:.1f} "
              f"({rt['cost_pct_of_buy']:.2f}% of buy)  net P&L ₹{rt['net_pnl']:.1f}")
