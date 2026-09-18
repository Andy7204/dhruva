"""LIVE news overlay — Google News RSS per stock, with a crude risk/earnings flag.

IMPORTANT: This is a LIVE, UN-BACKTESTED overlay. There is no free point-in-time
news history, so this cannot be validated the way the price strategy is. Use it
only as a human review step ("anything blowing up in a name before I act?"), never
as a trusted signal. Headlines are current-only.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# words that suggest something material to eyeball before buying/holding
RISK_WORDS = ["fraud", "probe", "raid", "sebi", "default", "downgrade", "resign",
              "block deal", "stake sale", "ban", "investigation", "insolvency",
              "scam", "pledge", "fire", "recall", "lawsuit", "penalty", "fined",
              "cut to", "slumps", "plunge", "crash", "layoff", "warning"]
EARNINGS_WORDS = ["q1", "q2", "q3", "q4", "results", "earnings", "profit", "revenue",
                  "guidance", "dividend", "bonus", "split"]

_NAMES = None


def _names() -> dict:
    global _NAMES
    if _NAMES is None:
        try:
            _NAMES = json.loads((PROJECT_ROOT / "data" / "nse_names.json").read_text())
        except Exception:
            _NAMES = {}
    return _NAMES


def company_name(ticker: str) -> str:
    return _names().get(ticker) or _names().get(ticker + ".NS") or ticker.replace(".NS", "")


def fetch_headlines(query: str, n: int = 5) -> list[dict]:
    q = urllib.parse.quote(f"{query} share NSE")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        xml = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": _UA}), timeout=20
        ).read().decode("utf-8", "ignore")
    except Exception:
        return []
    out = []
    for block in re.findall(r"<item>(.*?)</item>", xml, re.S)[:n]:
        t = re.search(r"<title>(.*?)</title>", block, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", block, re.S)
        title = re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1)).strip() if t else ""
        out.append({"title": title, "date": (d.group(1)[:16] if d else "")})
    return out


def flag(headlines: list[dict]) -> str:
    text = " ".join(h["title"].lower() for h in headlines)
    if any(w in text for w in RISK_WORDS):
        return "RISK"
    if any(re.search(rf"\b{re.escape(w)}\b", text) for w in EARNINGS_WORDS):
        return "EARNINGS"
    return "quiet"


def check(ticker: str, n: int = 5, pause: float = 0.3) -> dict:
    name = company_name(ticker)
    heads = fetch_headlines(name, n)
    time.sleep(pause)
    return {"ticker": ticker, "name": name, "flag": flag(heads), "headlines": heads}


if __name__ == "__main__":
    for t in ["RELIANCE.NS", "TITAN.NS", "ANANDRATHI.NS"]:
        r = check(t)
        print(f"\n{r['name']} [{r['flag']}]")
        for h in r["headlines"][:3]:
            print(f"  [{h['date']}] {h['title'][:85]}")
