"""Simple, insight-first HTML dashboard for the momentum paper book.

Layout (top = most important):
  1. Today's call — buy / hold / sell / stay-in-cash, with sizes & stops
  2. Scorecard vs Nifty + equity curve
  3. Current holdings
  4. Can this be trusted? (walk-forward, survivorship check, year-by-year)
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from qlab import metrics as M

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"


def _fmt(x, dp=0):
    try:
        return f"{x:,.{dp}f}"
    except (TypeError, ValueError):
        return str(x)


def _pnl(x, dp=0):
    try:
        cls = "pos" if x > 0 else ("neg" if x < 0 else "")
        return f'<span class="{cls}">{_fmt(x, dp)}</span>'
    except TypeError:
        return str(x)


def _table(headers, rows):
    th = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def _svg_equity(series, height=260):
    all_vals = [v for _, pts, _ in series for _, v in pts]
    if not all_vals:
        return "<p class='muted'>No history yet.</p>"
    lo, hi = min(all_vals), max(all_vals)
    span = (hi - lo) or 1.0
    W, H, pad = 1000, height, 8
    def X(i, n): return pad + (W - 2 * pad) * (i / max(n - 1, 1))
    def Y(v): return pad + (H - 2 * pad) * (1 - (v - lo) / span)
    polys = []
    for label, pts, color in series:
        coords = " ".join(f"{X(i, len(pts)):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(pts))
        polys.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{coords}"/>')
    base = series[0][1][0][1] if series[0][1] else lo
    grid = f'<line x1="{pad}" y1="{Y(base):.1f}" x2="{W-pad}" y2="{Y(base):.1f}" stroke="var(--grid)" stroke-dasharray="4 4"/>'
    legend = " &nbsp; ".join(f'<span style="color:{c};font-weight:600">&#9632; {html.escape(l)}</span>'
                             for l, _, c in series)
    return (f'<div class="legend">{legend}</div><svg viewBox="0 0 {W} {H}" '
            f'preserveAspectRatio="none" style="width:100%;height:{H}px">{grid}{"".join(polys)}</svg>')


def _load_validation():
    p = PROJECT_ROOT / "runs" / "validation.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _call_html(call, ccy):
    if not call:
        return ""
    on = call["risk_on"]
    color = "#12855a" if on else "#c4362f"
    head = (f'<div class="callhead" style="color:{color}">'
            f'{"● RISK-ON" if on else "● RISK-OFF"}</div>'
            f'<p>{html.escape(call["headline"])}</p>'
            f'<p class="muted">Nifty {_fmt(call["nifty"])} vs its {call["ma"]}-day avg '
            f'{_fmt(call["nifty_ma"])}. As of {call["date"]}.</p>')
    body = ""
    if on and call["buys"]:
        rows = [[f'<b>{html.escape(b["symbol"])}</b>', html.escape(b["sector"][:18]),
                 _fmt(b["price"], 1), f'{b["qty"]} sh · {ccy}{_fmt(b["invest"])}',
                 f'{b["weight_pct"]}%', _fmt(b["stop"], 1),
                 _pnl(-b["risk_rupees"]), _pnl(b["win_case_rupees"])]
                for b in call["buys"]]
        body += ("<h3>Buy today (equal-ish, vol-adjusted)</h3>"
                 + _table(["Stock", "Sector", "Price", "Buy", "Wt", "Stop",
                           "Risk if stopped", "Win-case*"], rows))
    elif on:
        body += "<p class='muted'>Risk-on, but no new names cleared the filters today.</p>"
    else:
        body += (f'<div class="cash">➜ Recommended stance: <b>hold {ccy} '
                 f'{_fmt(call["cash"])} in cash.</b> No new buys.</div>')
    if call.get("defensive_basket"):
        rows = [[f'<b>{html.escape(d["symbol"])}</b>', f'{ccy}{_fmt(d["value"])}',
                 _pnl(d["unrealized"])] for d in call["defensive_basket"]]
        body += ("<h3>Diversifier basket (held for protection)</h3>"
                 + _table(["Asset", "Value", "Unreal P&L"], rows))
    if call["holdings_actions"]:
        rows = [[f'<b>{html.escape(a["symbol"])}</b>', a["action"], _fmt(a["price"], 1),
                 _pnl(a["unrealized"]), html.escape(a["reason"])]
                for a in call["holdings_actions"]]
        body += "<h3>On current stock holdings</h3>" + _table(
            ["Stock", "Action", "Price", "Unreal P&L", "Why"], rows)
    note = (f'<p class="muted">*Win-case = if it performs like the strategy\'s average '
            f'winner (+{call["avg_win_pct"]}%); typical loser is {call["avg_loss_pct"]}%. '
            f'No fixed target — exits are rule-based. Illustration, not a forecast.</p>')
    return f'<div class="card callcard">{head}{body}{note}</div>'


def _trust_html(val, ccy):
    if not val:
        return ""
    wf = val.get("wf_500", {}); n100 = val.get("n100", {}); base = val.get("baselines", {})
    lines = []
    lines.append(f'<b>Walk-forward, 500 stocks (never saw the future):</b> '
                 f'trader {_pnl(wf.get("ret",0),1)}% vs Nifty {wf.get("nifty",0)}% · '
                 f'Sharpe {wf.get("sharpe",0)} · worst dip {wf.get("dd",0)}%')
    lines.append(f'<b>Survivorship-robust (Nifty-100 large caps):</b> walk-forward '
                 f'trader {_pnl(n100.get("wf_ret",0),1)}% vs Nifty {n100.get("wf_nifty",0)}% '
                 f'· Sharpe {n100.get("wf_sharpe",0)}')
    lines.append(f'<b>Vs basic strategies:</b> Nifty buy&hold {base.get("nifty_bh",0)}% · '
                 f'own-all-equally {base.get("equal_weight_bh",0)}%')
    ybl = val.get("year_by_year", {})
    yrows = [[y, _pnl(v["trader"], 1) + "%", _pnl(v["nifty"], 1) + "%",
              ("✅ beat" if v["beat"] else "✗ lag")] for y, v in ybl.items()]
    ytab = _table(["Year", "Trader", "Nifty", ""], yrows) if yrows else ""
    folds = wf.get("folds", [])
    frow = " · ".join(f'{f["test"][:7]}: {f["oos"]:+.0f}%' for f in folds)
    return ('<div class="card"><ul>' + "".join(f"<li>{x}</li>" for x in lines) + "</ul>"
            + (f'<p class="muted">Walk-forward folds: {frow}</p>' if frow else "")
            + "<h3>Year by year</h3>" + ytab + "</div>")


_CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#12151c;--muted:#6b7280;--line:#e6e8ec;--grid:#c9ccd2;--pos:#12855a;--neg:#c4362f;--accent:#0c6b73}
@media(prefers-color-scheme:dark){:root{--bg:#0f1216;--card:#171b21;--ink:#e8eaed;--muted:#9aa0aa;--line:#252b33;--grid:#39414c;--accent:#33b7bf}}
*{box-sizing:border-box}body{margin:0;font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
.wrap{max-width:1000px;margin:0 auto;padding:22px}
h1{font-size:20px;margin:0}h2{font-size:13px;margin:22px 0 8px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
h3{font-size:13px;margin:14px 0 6px}.sub{color:var(--muted);font-size:12.5px}
.disc{background:#fff7ed;border:1px solid #f0c48a;color:#7a4a12;padding:7px 11px;border-radius:8px;font-size:12px;margin:10px 0}
@media(prefers-color-scheme:dark){.disc{background:#2a2114;border-color:#5a4726;color:#e9c48a}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px;overflow-x:auto}
.callcard{border-width:2px}.callhead{font-size:20px;font-weight:800;margin-bottom:4px}
.cash{font-size:15px;padding:10px;border:1px dashed var(--grid);border-radius:8px;margin:6px 0}
.verdict{border:2px solid;border-radius:10px;padding:11px 15px;margin:10px 0;font-size:15px;background:var(--card)}
.book{border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px;background:var(--card)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:9px;margin:4px 0}
.kpi{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:10px}
.kv{font-size:17px;font-weight:700}.kl{color:var(--muted);font-size:11px;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:12.5px}th,td{text-align:right;padding:6px 8px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:600}td:last-child,th:last-child{text-align:left}
.pos{color:var(--pos);font-weight:600}.neg{color:var(--neg);font-weight:600}.muted{color:var(--muted)}
.legend{font-size:12px;margin-bottom:6px}ul{margin:4px 0;padding-left:18px}li{margin:3px 0}
"""


def _kpi_row(pairs):
    return ('<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="kv">{v}</div><div class="kl">{html.escape(k)}</div></div>'
        for k, v in pairs) + "</div>")


def _load_backtest():
    try:
        return json.loads((PROJECT_ROOT / "runs" / "backtest_comparison.json").read_text())
    except Exception:
        return None


def _backtest_html(bt, ccy):
    if not bt:
        return "<div class='card muted'>Run scripts/compare3.py to populate the backtest.</div>"
    colors = {"Balanced": "#2f6df6", "Aggressive-smart": "#c4362f",
              "Core-satellite 70/30": "#12855a", "Nifty": "#e0803a"}
    strat = [n for n in bt["ratios"]]
    order = strat + ["Nifty"]
    series = [(n, [(d, v) for d, v in bt["curves"][n]], colors.get(n, "#888"))
              for n in order if n in bt["curves"]]
    rrows = []
    for lbl, key in [("Total return", "total_return_pct"), ("CAGR", "cagr_pct"),
                     ("Sharpe", "sharpe"), ("Sortino", "sortino"),
                     ("Calmar", "calmar"), ("Worst dip", "max_drawdown_pct")]:
        pct = "%" if key.endswith("pct") else ""
        rrows.append([lbl] + [_fmt(bt["ratios"][n][key], 2) + pct for n in strat])
    rtab = _table(["Metric"] + strat, rrows)
    yrows = [[yr, _pnl(d["Nifty"], 1) + "%"] + [_pnl(d[n], 1) + "%" for n in strat]
             for yr, d in bt["year_by_year"].items()]
    ytab = _table(["Year", "Nifty"] + strat, yrows)
    beats = bt.get("beats", {})
    beatline = " · ".join(f"{n.split()[0]} beat Nifty in {beats.get(n, 0)} of {bt['years']} yrs" for n in strat)
    return (f"<p class='muted'>How each strategy would have done over {bt['window'][0]} → "
            f"{bt['window'][1]} (~{bt['years']} yrs). The Nifty returned <b>{bt['nifty_total']}%</b> "
            f"over the same window. This is the evidence behind the live book above.</p>"
            f"<div class='card'>{_svg_equity(series)}</div>"
            f"<h3>Scorecard (₹1,00,000 in each)</h3><div class='card overflow'>{rtab}</div>"
            f"<h3>Year by year</h3><div class='card overflow'>{ytab}"
            f"<p class='muted' style='margin-top:8px'>{beatline}. Note: each beats the index only a "
            f"couple of years, yet wins big overall — momentum's up-years are explosive, so you must "
            f"sit through the flat years to collect them.</p></div>")


def build_multi_dashboard(cfg, results, bench_series, out_path=None, narrative=None) -> Path:
    """Two-tier dashboard: a live book started today, then the backtested history."""
    out_path = Path(out_path) if out_path else REPORTS_DIR / "dashboard.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ccy = cfg["base_currency"]
    labels = {"balanced": "balanced core", "aggressive": "aggressive satellite"}
    start_total = sum(r["capital"] for r in results)
    states = [r["state"] for r in results]
    as_of = states[0].get("as_of", "—")
    inception = states[0].get("inception", as_of)
    days = max(s.get("step_count", 0) for s in states)
    risk_on = states[0].get("risk_on", False)

    # ---- combine the books into one live portfolio ----
    cash = sum(s["cash"] for s in states)
    holds = {}
    for r in results:
        for sym, h in r["state"]["holdings"].items():
            px = r["prices_now"].get(sym, h.get("avg", 0))
            g = holds.setdefault(sym, {"qty": 0, "value": 0.0, "avg": h.get("avg", 0),
                                       "kind": h["kind"], "settled": h.get("settled", False)})
            g["qty"] += h["qty"]; g["value"] += h["qty"] * px
    cur_total = cash + sum(h["value"] for h in holds.values())
    ret = (cur_total / start_total - 1) * 100
    charges = sum(s.get("charges_total", 0) for s in states)

    frames = {r["name"]: pd.Series({pd.Timestamp(d): v for d, v in r["state"].get("history", [])})
              for r in results}
    combined = (pd.DataFrame(frames).sort_index().ffill().sum(axis=1).dropna()
                if any(len(f) for f in frames.values()) else pd.Series(dtype=float))
    if days >= 40 and len(combined) > 3:
        cm = M.compute_metrics(combined, [])
        stat_extra = [("CAGR", _fmt(cm["cagr_pct"], 1) + "%"), ("Sharpe", _fmt(cm["sharpe"], 2)),
                      ("Sortino", _fmt(cm["sortino"], 2)), ("Worst dip", _fmt(cm["max_drawdown_pct"], 1) + "%")]
    else:
        stat_extra = [("CAGR", "building"), ("Sharpe", "building"),
                      ("Sortino", "building"), ("Worst dip", "—")]
    tax_due = sum(s.get("tax_accrued", 0) for s in states)
    tax_detail = {}
    for s in states:
        for k, v in (s.get("tax_detail") or {}).items():
            tax_detail[k] = tax_detail.get(k, 0) + v
    kpis = _kpi_row([("Total value", f"{ccy} {_fmt(cur_total)}"), ("Return", _pnl(ret, 1) + "%"),
                     ("Cash", f"{cash / cur_total * 100:.0f}%" if cur_total else "—"),
                     ("Day", str(days)), ("Fees paid", f"{ccy} {_fmt(charges)}"),
                     ("Tax provision", f"{ccy} {_fmt(tax_due)}")] + stat_extra)

    # order lifecycle
    all_orders = [o for r in results for o in r["state"]["orders"]]
    scheduled = [o for o in all_orders if o["status"] == "scheduled"]
    filled_today = [o for o in all_orders if o.get("fill_date") == as_of and o["status"] in ("filled", "settled")]

    def _orows(orders):
        rows = []
        for o in orders:
            if o["side"] == "BUY":
                detail = f'buy ≈ {ccy}{_fmt(o.get("target_value") or o.get("amount") or 0)}'
                detail += f' (near {ccy}{_fmt(o.get("ref_price"), 1)})' if o.get("ref_price") else ""
            else:
                detail = f'sell {o.get("qty", "all")}' + (f' · {o.get("reason", "")}' if o.get("reason") else "")
            rows.append([o["side"], f'<b>{html.escape(o["symbol"].replace(".NS", ""))}</b>',
                         o.get("kind", ""), detail,
                         f'{ccy}{_fmt(o.get("cost", 0))}' if o.get("cost") else "on fill"])
        return rows

    on_color = "#12855a" if risk_on else "#c4362f"
    head_txt = "● RISK-ON — deploying into momentum leaders" if risk_on else "● RISK-OFF — defensive"
    instr = ("The market is above its long-term trend. Place the scheduled orders below at the next open."
             if risk_on else
             "The Nifty is below its 200-day trend — no new stock buys. Only the defensive cushion is placed; "
             "the rest waits in cash.")
    orders_html = ""
    if scheduled:
        orders_html += ("<h3>Scheduled — place these at the next market open</h3>"
                        + _table(["Side", "Symbol", "Type", "Order", "Est. cost"], _orows(scheduled))
                        + "<p class='muted'>These fill at the NEXT session's OPEN price and settle T+1 — "
                          "about 1–2 trading days before they actually reach your demat.</p>")
    else:
        orders_html += '<div class="cash">No orders scheduled for the next session — hold as is.</div>'
    if filled_today:
        orders_html += ("<h3>Filled today — now settling (T+1)</h3>"
                        + _table(["Side", "Symbol", "Type", "Order", "Charges"], _orows(filled_today)))
    decision = (f'<div class="card callcard" style="border-color:{on_color}">'
                f'<div class="callhead" style="color:{on_color}">{head_txt}</div>'
                f'<p>{instr}</p>{orders_html}</div>')

    # holdings (incl cash) with settlement status
    hrows = []
    for sym, h in sorted(holds.items(), key=lambda kv: -kv[1]["value"]):
        px = h["value"] / h["qty"] if h["qty"] else h["avg"]
        hrows.append([sym.replace(".NS", ""), h["kind"], h["qty"], f'{ccy}{_fmt(h["value"])}',
                      _pnl((px - h["avg"]) * h["qty"]) if h["kind"] == "stock" else "—",
                      "in demat ✓" if h.get("settled") else "settling"])
    hrows.append(["<b>Cash</b>", "cash", "—", f'{ccy}{_fmt(cash)}', "—", "available"])
    holdings_tbl = _table(["Holding", "Type", "Qty", "Value", "Unreal P&L", "Status"], hrows)
    split = " + ".join(f'{ccy}{_fmt(r["capital"])} {labels.get(r["name"], r["name"])}' for r in results)

    # circuit-breaker + rebalance countdown
    next_rebal = states[0].get("next_rebalance_in")
    breaker = any(s.get("breaker") for s in states)
    breaker_banner = ('<div class="verdict" style="border-color:#c4362f">'
                      '<span style="color:#c4362f;font-weight:700">⚠ CIRCUIT-BREAKER ACTIVE</span> — '
                      'drawdown passed the limit; de-risked to the defensive basket + cash until it recovers.</div>'
                      if breaker else "")
    rebal_note = (f'<div class="sub" style="margin-top:4px">Next scheduled rebalance in ~<b>{next_rebal}</b> '
                  f'trading days (that\'s when the stock list can change).</div>' if next_rebal else "")

    # trade journal (combined, most recent fills first)
    journal = sorted([o for r in results for o in r["state"]["orders"] if o.get("fill_date")],
                     key=lambda o: o["fill_date"], reverse=True)[:25]
    jrows = [[o["fill_date"], o["side"], o["symbol"].replace(".NS", ""), o.get("qty", "—"),
              f'{ccy}{_fmt(o.get("amount", 0))}', f'{ccy}{_fmt(o.get("cost", 0))}',
              html.escape(o.get("reason", "rebalance"))] for o in journal]
    journal_tbl = (_table(["Filled", "Side", "Symbol", "Qty", "Amount", "Charges", "Note"], jrows)
                   if jrows else "<span class='muted'>No trades filled yet — first orders are scheduled for the next open.</span>")
    tax_rows = "".join(f"<li>{html.escape(k)}: {ccy}{_fmt(v)}</li>" for k, v in tax_detail.items())
    tax_html = (f"<p class='muted'>Tax provision breakdown:</p><ul>{tax_rows}</ul>" if tax_rows else "")

    bt_html = _backtest_html(_load_backtest(), ccy)
    trust = _trust_html(_load_validation(), ccy)

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Dhruva</title>
<style>{_CSS}</style></head><body><div class="wrap">
<h1>Dhruva <span style="font-weight:400;color:var(--muted);font-size:15px">· your steadfast momentum engine</span></h1>
<div class="sub">{ccy} {_fmt(start_total)} · started {inception} · Day {days} · updated {as_of}</div>

<h2>Your ₹1,00,000 — live from today</h2>
{f'<div class="card" style="border-left:3px solid var(--accent)"><b>In plain words</b><p style="margin:6px 0 0">{html.escape(narrative)}</p></div>' if narrative else ''}
{breaker_banner}
{decision}
{kpis}
{rebal_note}
<h3>What you're holding now</h3>
<div class="card overflow">{holdings_tbl}</div>
<div class="sub">Split: {split}. Follow both calls together — that is the core-satellite 70/30.</div>
<div class="sub" style="margin-top:5px">Every fill (stocks <b>and</b> ETFs like GOLDBEES) pays Groww charges, and realised gains accrue capital-gains tax — equity STCG 20% / LTCG 12.5%, gold &amp; silver ETFs at slab / 12.5%. Both are set aside from your net worth so the number is honest. Verify tax with a CA.</div>
{tax_html}

<h2>Trade journal — every fill, with charges</h2>
<div class="card overflow">{journal_tbl}</div>

<h2>Backtested runs — how these strategies did in the past</h2>
{bt_html}

<h2>Can this be trusted?</h2>
{trust or '<div class="card muted">Run scripts/validate.py.</div>'}

<div class="sub" style="margin-top:16px">Momentum 12-1 · Groww costs · simulated paper trading for research — decisions &amp; risk are yours · past performance does not predict the future.</div>
</div></body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path


def build_dashboard(cfg, live_pf, metrics, bench_series, review_report,
                    prices_now, call=None, out_path=None) -> Path:
    out_path = Path(out_path) if out_path else REPORTS_DIR / "dashboard.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ccy = cfg["base_currency"]
    as_of = live_pf.get("as_of", "—")
    eq_hist = live_pf.get("equity_history", [])
    start_eq = cfg["starting_capital"]
    cur_eq = eq_hist[-1][1] if eq_hist else start_eq
    ret_pct = (cur_eq / start_eq - 1) * 100

    series = [("The trader", [(d, v) for d, v in eq_hist], "#2f6df6")]
    nifty_ret = None
    if bench_series is not None and len(bench_series) > 2 and eq_hist:
        dates = [pd.Timestamp(d) for d, _ in eq_hist]
        b = bench_series.reindex(dates).ffill().dropna()
        if len(b) > 2:
            scale = start_eq / b.iloc[0]
            nifty_ret = (b.iloc[-1] / b.iloc[0] - 1) * 100
            series.append(("Nifty buy & hold", [(str(i.date()), float(v * scale)) for i, v in b.items()], "#e0803a"))

    verdict = ""
    if nifty_ret is not None:
        beat = ret_pct > nifty_ret
        c = "#12855a" if beat else "#c4362f"
        verdict = (f'<div class="verdict" style="border-color:{c}">'
                   f'<span style="color:{c};font-weight:700">{"BEATING" if beat else "TRAILING"} the Nifty</span> '
                   f'· trader <b>{ret_pct:+.1f}%</b> vs Nifty <b>{nifty_ret:+.1f}%</b> '
                   f'· edge <b>{ret_pct-nifty_ret:+.1f}%</b> since {live_pf.get("inception","start")}</div>')

    kpis = [("Equity", f"{ccy} {_fmt(cur_eq)}"), ("Return", _pnl(ret_pct, 1) + "%"),
            ("Nifty", (_pnl(nifty_ret, 1) + "%") if nifty_ret is not None else "—"),
            ("Sharpe", _fmt(metrics.get("sharpe", 0), 2)),
            ("Worst dip", _fmt(metrics.get("max_drawdown_pct", 0), 1) + "%"),
            ("Fees", f"{ccy} {_fmt(metrics.get('total_charges', 0))}")]
    kpi_html = "".join(f'<div class="kpi"><div class="kv">{v}</div><div class="kl">{html.escape(k)}</div></div>'
                       for k, v in kpis)

    # holdings
    pos_rows = []
    for name, s in live_pf["sleeves"].items():
        for sym, p in s["positions"].items():
            px = prices_now.get(sym, p["avg_price"])
            pos_rows.append([sym.replace(".NS", ""), p["qty"], _fmt(p["avg_price"], 1),
                             _fmt(px, 1), _pnl((px - p["avg_price"]) * p["qty"]), _fmt(p["stop"], 1),
                             p["bars_held"]])
    holdings = (_table(["Stock", "Qty", "Entry", "Now", "Unreal P&L", "Stop", "Days"], pos_rows)
                if pos_rows else "<p class='muted'>Currently in cash — no open positions.</p>")

    call_html = _call_html(call, ccy)
    trust_html = _trust_html(_load_validation(), ccy)

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Momentum Trader</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#12151c;--muted:#6b7280;--line:#e6e8ec;--grid:#c9ccd2;--pos:#12855a;--neg:#c4362f}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1216;--card:#171b21;--ink:#e8eaed;--muted:#9aa0aa;--line:#252b33;--grid:#39414c}}}}
*{{box-sizing:border-box}}body{{margin:0;font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}}
.wrap{{max-width:1000px;margin:0 auto;padding:22px}}
h1{{font-size:20px;margin:0}}h2{{font-size:13px;margin:24px 0 8px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}}
h3{{font-size:13px;margin:14px 0 6px}}
.sub{{color:var(--muted);font-size:12.5px}}
.disc{{background:#fff7ed;border:1px solid #f0c48a;color:#7a4a12;padding:7px 11px;border-radius:8px;font-size:12px;margin:10px 0}}
@media(prefers-color-scheme:dark){{.disc{{background:#2a2114;border-color:#5a4726;color:#e9c48a}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px;overflow-x:auto}}
.callcard{{border-width:2px}}.callhead{{font-size:22px;font-weight:800;margin-bottom:4px}}
.cash{{font-size:16px;padding:10px;border:1px dashed var(--grid);border-radius:8px;margin:6px 0}}
.verdict{{border:2px solid;border-radius:10px;padding:11px 15px;margin:10px 0;font-size:15px;background:var(--card)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:9px;margin-bottom:4px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px}}
.kv{{font-size:18px;font-weight:700}}.kl{{color:var(--muted);font-size:11.5px;margin-top:2px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid var(--line)}}
th:first-child,td:first-child{{text-align:left}}th{{color:var(--muted);font-weight:600}}td:last-child,th:last-child{{text-align:left}}
.pos{{color:var(--pos);font-weight:600}}.neg{{color:var(--neg);font-weight:600}}.muted{{color:var(--muted)}}
.legend{{font-size:12px;margin-bottom:6px}}ul{{margin:4px 0;padding-left:18px}}li{{margin:3px 0}}
</style></head><body><div class="wrap">
<h1>Momentum Trader — daily call</h1>
<div class="sub">{ccy} {_fmt(start_eq)} start · as of <b>{as_of}</b> · Nifty-500 momentum, top {cfg['sleeves']['long_term']['max_positions']}</div>
<div class="disc"><b>Educational research only — not investment advice.</b> Virtual money, simulated fills, no real orders. The author is not a licensed adviser; any real-money decision and its risk are yours.</div>

<h2>Today's call</h2>
{call_html}

<h2>Track record (paper, forward-tested)</h2>
{verdict}
<div class="kpis">{kpi_html}</div>
<div class="card">{_svg_equity(series)}</div>

<h2>Current holdings</h2>
<div class="card">{holdings}</div>

<h2>Can this be trusted?</h2>
{trust_html or '<div class="card muted">Run scripts/validate.py to populate the trust checks.</div>'}

<div class="sub" style="margin-top:16px">Momentum 12-1 · liquidity + sector-cap filters · Groww costs · crash filter (Nifty vs 200-DMA). Past performance does not predict the future.</div>
</div></body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path
