# Inflection radar — finding Sandisk-like setups early

Paper research added September29, 2026 at the owner's request. It is a research
aid, not investment advice, and it never places or assumes trades.

## What a Sandisk-like move looked like in the data

Sandisk (SNDK, US-listed) listed at $36 in February 2025, bottomed at $29.6 in
April 2025 and peaked at $2,335 in June 2026 (about 79 times the low). Its
quarterly numbers changed character before and during the move:

| Quarter ending | Revenue ($m) | Gross margin | Net income ($m) | EPS |
|---|---:|---:|---:|---:|
| Jun 2025 | 1,901 | 26% | -23 | -0.16 |
| Sep 2025 | 2,308 | 30% | 112 | 0.75 |
| Dec 2025 | 3,025 | 51% | 803 | 5.15 |
| Mar 2026 | 5,950 | 78% | 3,615 | 23.03 |
| Jun 2026 | 8,965 | 85% | 6,903 | 43.97 |

The pattern: an industry-wide pricing upcycle (NAND memory), revenue accelerating
quarter after quarter, margins expanding (pricing power), a swing from loss to
profit, and earnings growing far faster than revenue (operating leverage). Price
moved first: a stage-2 breakout on heavy volume on August 29, 2025 at about $52;
the profit turnaround was only visible in results reported around November 2025.
A 50-day-average trailing exit would have sold on March 30, 2026 at $572 (11.2×)
and missed the second leg, which is why exits are thesis-based, not only price-based.

This is one hand-picked winner. Many companies show similar early numbers and do
not become multibaggers; the funnel exists to find candidates worth deep research.

## The three stages

1. **Stage 1 — quantitative scan of about 750 stocks** (`scanner/score.py`), daily.
   Universe: official Nifty Total Market list (Nifty 500 + Microcap 250). Scores 0–100:
   revenue acceleration 15, operating leverage 15 (EBITDA growth versus revenue growth,
   incremental EBITDA margin, margin change), PAT/EPS acceleration 15 (turnaround counts
   fully), earnings quality 10 (one-off items, tax rate), cash-flow forensics 15 (CFO/PAT,
   receivables and inventory versus revenue, cash-flow class A–D), balance sheet 10
   (net debt/EBITDA, interest cover, dilution), valuation gap 15 (PEG, EPS growth minus
   12-month price return, size) and filing catalysts 5 (orders, capacity commissioning).
   Serious filings veto (insolvency, auditor resignation, default, fraud); routine
   litigation and tax orders are only flagged. Price trend does not add to the score.
2. **Stage 2 — narrow to 10** (`scanner/stage2.py`). Adds industry-wide inflection (share
   of peers with revenue growth above 20% and expanding margins: a proxy for a demand
   shock or pricing power), Stage 1 score momentum over 20 sessions, and capacity filings.
   At most three finalists per industry. Writes an evidence dossier per finalist with the
   numbers and NSE filing links (results, presentations, call transcripts, orders).
3. **Stage 3 — Claude deep underwriter** (`underwriter/run.py`, prompt in
   `prompts/underwriter.md`). Runs the owner's full framework on a finalist only when
   something changed: first review, Stage 2 score moved 5+ points, a new result,
   presentation, order or capacity filing, or 30 days since the last review. At most
   three per day (`UNDERWRITER_MAX`). Claude reads filings and industry sources with web
   search, scores the 100-point Sandisk detector, writes bear/base/bull/extreme cases with
   FY+2/+3/+5 EPS and exit P/E, tests 2×/3×/5×/10×, sets kill conditions and chooses
   BUY/ADD/HOLD/WAIT/TRIM/EXIT/REJECT. Each review is appended to
   `runs/inflection/db/<SYMBOL>.json`; `runs/inflection/report.md` is the daily report.

## Capital and trades

INR10,000 is credited on the first session of each month and rolls over. A BUY or ADD
recommendation is only a paper recommendation. Holdings change only when the owner
confirms an executed trade, by telling Claude Code or appending a line to
`runs/inflection/confirmed_trades.jsonl`:

```json
{"date": "2026-10-05", "symbol": "ELLEN", "side": "BUY", "qty": 20, "price": 370.5, "fees": 20}
```

## Timing aids (not part of the score)

Stage 1 records a stage-2 trend flag (price above rising 150/200-day averages, within 25%
of the 52-week high), relative-strength rank, and a breakout flag (close above the prior
50-day high on at least 1.5× average volume). These help time an entry after the thesis
is underwritten; a close more than 3% below the 50-day average is a warning to re-check
the thesis, not an automatic sale.

## Limits

- Free data gives only five quarters (Yahoo) and no consensus estimates, order-book
  size, capacity utilization or promoter pledges. Stage 3 must find these or say unknown.
- No point-in-time fundamentals or delisted companies are available, so the scanner
  cannot be honestly backtested. It is evaluated forward: every Stage 1–3 output is dated
  and kept (`score_history.csv`, `funnel_history.jsonl`, the thesis database).
- NSE endpoints may block cloud IP addresses; then filing signals are marked unavailable.
- Stage 3 needs an `ANTHROPIC_API_KEY` repository secret and costs money per review;
  without it Stages 1–2 still run daily.
