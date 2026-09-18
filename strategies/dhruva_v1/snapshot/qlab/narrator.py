"""Daily narrator — a plain-English explanation of today's call.

Deterministic decisions in, human words out. It NEVER changes a decision or adds
advice; it only rephrases the day's facts. If an LLM key is present
(ANTHROPIC_API_KEY or OPENAI_API_KEY) it polishes the prose; otherwise a built-in
rule-based writer produces a solid explanation with zero dependencies/keys — so it
always runs in the autonomous cron.
"""
from __future__ import annotations

import json
import os
import urllib.request


def _facts(cfg, results) -> dict:
    ccy = cfg["base_currency"]
    s0 = results[0]["state"]
    start = sum(r["capital"] for r in results)
    val = 0.0
    for r in results:
        h = r["state"].get("history", [])
        val += h[-1][1] if h else r["capital"]
    orders = []
    for r in results:
        for o in r["state"]["orders"]:
            if o["status"] == "scheduled":
                orders.append({"book": r["name"], "side": o["side"],
                               "symbol": o["symbol"].replace(".NS", ""),
                               "amount": o.get("target_value"), "reason": o.get("reason", "")})
    breaker = any(r["state"].get("breaker") for r in results)
    return {"date": s0.get("as_of"), "ccy": ccy, "value": round(val), "start": start,
            "return_pct": round((val / start - 1) * 100, 1), "day": s0.get("step_count"),
            "risk_on": s0.get("risk_on"), "circuit_breaker": breaker,
            "next_rebalance_in": s0.get("next_rebalance_in"), "orders": orders}


def _rule_based(f: dict) -> str:
    ccy = f["ccy"]
    p = [f"As of {f['date']} (day {f['day']}), Dhruva is worth {ccy}{f['value']:,} "
         f"({f['return_pct']:+.1f}% since you started with {ccy}{f['start']:,})."]
    if f["circuit_breaker"]:
        p.append("The circuit-breaker is ON — the book fell past its drawdown limit, so it has "
                 "de-risked into the defensive cushion and cash until it recovers.")
    elif f["risk_on"]:
        p.append("The market is above its long-term (200-day) trend, so the strategy is happy to "
                 "hold momentum leaders.")
    else:
        p.append("The market is below its 200-day trend, so — by rule — it buys no new stocks today; "
                 "it holds the defensive cushion (gold/silver/InvIT) and keeps the rest in cash, "
                 "waiting for the trend to turn back up.")
    buys = [o for o in f["orders"] if o["side"] == "BUY"]
    sells = [o for o in f["orders"] if o["side"] == "SELL"]
    if buys:
        p.append("To place at the next market open: " +
                 ", ".join(f"buy {o['symbol']} (~{ccy}{o['amount']:,.0f})" for o in buys) +
                 ". These fill at tomorrow's opening price and settle in about a day.")
    if sells:
        p.append("Selling: " + ", ".join(f"{o['symbol']} ({o['reason']})" for o in sells) + ".")
    if not buys and not sells:
        p.append("No orders to place today — just hold what you have.")
    if f.get("next_rebalance_in"):
        p.append(f"The next scheduled review of the stock list is in about {f['next_rebalance_in']} "
                 f"trading days.")
    p.append("(Automated, rules-based paper trading — not advice.)")
    return " ".join(p)


def _llm(f: dict) -> str | None:
    facts = json.dumps(f)
    prompt = ("You explain a rules-based paper-trading system's automated daily decision to a "
              "beginner in 4-6 warm, plain sentences. Rephrase ONLY these facts — do not add "
              "advice, predictions, or new numbers, and do not change any decision. End by noting "
              "it is automated paper trading, not advice.\nFacts:\n" + facts)
    ak = os.environ.get("ANTHROPIC_API_KEY")
    if ak:
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({"model": os.environ.get("NARRATOR_MODEL", "claude-haiku-4-5-20251001"),
                                 "max_tokens": 400,
                                 "messages": [{"role": "user", "content": prompt}]}).encode(),
                headers={"x-api-key": ak, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=30).read())
            return r["content"][0]["text"].strip()
        except Exception:
            return None
    ok = os.environ.get("OPENAI_API_KEY")
    if ok:
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({"model": os.environ.get("NARRATOR_MODEL", "gpt-4o-mini"),
                                 "messages": [{"role": "user", "content": prompt}]}).encode(),
                headers={"Authorization": f"Bearer {ok}", "content-type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=30).read())
            return r["choices"][0]["message"]["content"].strip()
        except Exception:
            return None
    return None


def narrate(cfg, results) -> str:
    f = _facts(cfg, results)
    return _llm(f) or _rule_based(f)
