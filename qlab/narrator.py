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
import hashlib
from datetime import datetime, timezone


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
            "next_rebalance_in": s0.get("next_rebalance_in"), "orders": orders,
            "holdings": sorted({s for r in results for s in r['state']['holdings']}),
            "limitations": 'Paper only; modeled costs/tax; unverified distribution income excluded.'}


def _rule_based(f: dict) -> str:
    ccy = f["ccy"]
    p = [f"As of {f['date']} (day {f['day']}), Dhruva is worth {ccy}{f['value']:,} "
         f"({f['return_pct']:+.1f}% since you started with {ccy}{f['start']:,})."]
    if f["circuit_breaker"]:
        p.append("The circuit-breaker is ON in at least one book. Stock reduction follows the "
                 "recorded orders and execution checks; a scheduled sale is not a completed sale.")
    elif f["risk_on"]:
        p.append("The market is above its long-term (200-day) trend, so the strategy is happy to "
                 "hold momentum leaders.")
    else:
        p.append("The market filter is defensive. New stock allocation is restricted; existing "
                 "holdings still follow their exit rules. A trend recovery does not itself trigger an immediate rebalance.")
    if f.get('holdings'):
        p.append('Recorded holdings: '+', '.join(f['holdings'])+'.')
    buys = [o for o in f["orders"] if o["side"] == "BUY"]
    sells = [o for o in f["orders"] if o["side"] == "SELL"]
    if buys:
        p.append("Pending paper buy intents: " +
                 ", ".join(f"buy {o['symbol']} (~{ccy}{o['amount']:,.0f})" for o in buys) +
                 ". Fills use the next eligible session's open, subject to prices, cash, risk and settlement checks; they may remain pending or be cancelled.")
    if sells:
        p.append("Pending paper sell intents: " + ", ".join(f"{o['symbol']} ({o['reason']})" for o in sells) + ".")
    if not buys and not sells:
        p.append("HOLD: no pending paper orders in the saved books.")
    if f.get("next_rebalance_in"):
        p.append(f"The next scheduled review of the stock list is in about {f['next_rebalance_in']} "
                 f"trading days.")
    p.append("Modeled costs and tax apply; unverified distribution income is excluded. (Automated paper trading — not advice.)")
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
    return narrate_with_metadata(cfg,results)['text']


def narrate_with_metadata(cfg, results) -> dict:
    f = _facts(cfg, results)
    generated=_llm(f)
    provider=('anthropic' if os.environ.get('ANTHROPIC_API_KEY') else 'openai') if generated else 'rules'
    text=('AI wording (unverified; saved orders are authoritative): '+generated) if generated else _rule_based(f)
    return {'generated_at':datetime.now(timezone.utc).isoformat(),'facts':f,'source':provider,
            'text':text,'text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'scope':'Explanation only; cannot change orders or fills'}
