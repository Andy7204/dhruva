# Dhruva inflection architecture v3 — early detection with staged conviction

Written October 3, 2026 after the Sterlite Technologies (STL) miss, comparing the
owner's revised Inflection Portfolio framework with the Stage 1–2–3 pipeline built
on September 29. Facts about STL below come from its NSE filings and Yahoo prices;
calculations are labelled. Paper research, not investment advice.

## 0. What actually happened with STL (point-in-time facts)

| Date (2026) | Public information | Close near date |
|---|---|---|
| Jan 23 | Q3 FY26 results: revenue Rs1,257 cr, operating profit Rs41 cr, net loss Rs17 cr | ~Rs88–106 |
| Feb 2–3 | NSE asks the company to explain unusual **price movement** (exchange surveillance) | ~Rs106–133 |
| Feb 7 | Promoter Twin Star subscribes to up to 4.53 cr **warrants at Rs110** = Rs498 cr (about 10% of market cap) | ~Rs133–156 |
| Mar 25, Apr 20 | Hollow-core fibre for data centres; "Neuralis" AI data-centre portfolio launched in the US | ~Rs186, ~Rs263 |
| Apr 29 | Q4 FY26: revenue Rs1,441 cr (+37% YoY), operating profit Rs135 cr (vs Rs52 cr), profit Rs59 cr (turnaround). FY26 revenue Rs4,745 cr, EBITDA margin 13.2% | ~Rs267–295 |
| May 22 | Hyperscaler **Product Award Letter, ~USD 1.11 bn** potential value, allocations FY27–FY29, POs released periodically, mutual capped liabilities | ~Rs441 |
| Jun 25–Jul 2 | QIP raises Rs1,500 cr | ~Rs577–613 |
| Jul 24 | Q1 FY27: revenue Rs1,910 cr (+87%), operating profit Rs300 cr, profit Rs197 cr | ~Rs520–564 |
| Aug 29 | Long-term agreement with a leading hyperscaler, CY2027–2029 | ~Rs724 |
| Sep 3 | Capacity addition ~50% by FY29, ~Rs3,000 cr capex, current utilization ~70% | ~Rs749 |
| Oct 1 | Hyperscaler LTSA ~USD 1.2 bn, CY2026–2030 | Rs955 (Oct 2) |

CALCULATION: USD 1.11 bn ≈ Rs9,400 cr over FY27–29 ≈ Rs3,100 cr a year ≈ 66% of
FY26 revenue per year. That single filing was the decisive public signal.

## 1. Answers to the fifteen questions

1. **Would the Sept-29 pipeline have caught STL in April/May? No.** Four reasons,
   in order of importance: (a) STL was **not in the universe** — the scanner reads only
   Nifty Total Market (~750 stocks) and STLTECH is not on that list; (b) Stage 1 is driven
   by reported results, so the earliest possible flag was April 29 (~Rs270–295, already
   3× the January low); (c) Stage 1 counts order filings but does not **size** them, so the
   May 22 USD 1.11 bn award scored the same as a small domestic order; (d) Stage 3's
   valuation discipline on trailing earnings would probably have said WAIT in May.
2. **Missing features:** universe breadth; order value relative to TTM revenue; promoter
   preferential subscription (price versus market, size versus market cap); exchange
   surveillance flags (price-movement and volume-spurt queries) joined to filings;
   product/geography mix shift; capacity utilization disclosures; forward-earnings
   scenarios that use disclosed contract values instead of trailing EPS.
3. **Where the Early Inflection Score sits: both, split.** Its *deterministic* parts
   (order intensity, capacity intensity, promoter buying, surveillance-plus-filing,
   margin inflection from a low base, turnaround) belong in Stage 1 so every stock gets
   them daily. Its *judgement* parts (demand acceleration, shortage, guidance change,
   mix shift) belong in Stage 2/3, extracted from documents.
4. **Fast lane: yes, but filtered.** Unfiltered, the triggers fire for ~100+ companies a
   month (measured Jun–Sep 2026: order filings 184 companies, volume spurts 219, price
   queries 144, capacity additions 65, preferential issues 21). Only events that pass a
   materiality test (section E) skip the ranking queue; everything else enters Stage 1 as
   a feature.
5. **Price-volume without becoming momentum:** use an anomaly only as a *join key*: an
   abnormal move (≥2.5 standard deviations or ≥8% on ≥3× volume) **with** a material filing
   within ±3 sessions opens a RESEARCH ticket. An anomaly without a filing is logged, not
   researched. Price never adds points to any score that drives buying, and STARTER is
   barred if the stock is already >60% above its 3-month low unless forward earnings
   justify the price.
6. **Staged sizing and Stage 3:** Stage 3 decides the *state*, not just a score. Each state
   has its own evidence bar (section G). Starters need asymmetry and one hard, numeric
   fact; adds need a new *independent* fact of a different kind than the one that justified
   entry; core size needs reported earnings and cash.
7. **Separate scores: yes — five, never added into one number.** Discovery (early),
   Confirmation, Valuation/expected value, Risk (governance, balance sheet, cycle), and an
   Action that is a rule over the four. A single blended score hides exactly the case
   that matters: high confirmation plus exhausted valuation.
8. **Missed-winner audit:** automatic triggers, point-in-time reconstruction from
   timestamped data only, and a matched control group for every candidate rule (section H).
9. **Hindsight bias:** reconstruct with only data stamped before each date; write the
   "would I have acted" decision before looking at the subsequent price; and score each
   candidate rule on non-winners that had the same signal on the same day.
10. **False positives:** a rule is adopted only if, on control samples, it raises precision
    and adds no more than a fixed research budget (e.g. 5 tickets a week); every adopted
    rule has a forward precision tracker and is retired if it fails.
11. **Deterministic Stage 1 features:** section E.1.
12. **LLM extraction in Stage 2:** section E.2 — numbers from PDFs, never opinions.
13. **Left to Claude in Stage 3:** whether the event is day 1 of a multi-year change,
    industry shortage duration, competitive response, management credibility, scenario
    probabilities, and kill conditions.
14. **Triggers for RESEARCH / STARTER / ADD / HOLD / TRIM / EXIT:** section G.
15. **Redesign for the stated objective:** sections D–I.

## 2. Critique of the new framework (where it can hurt)

- **Orders that never convert.** STL's awards are allocations with periodic POs and
  *mutual, capped* liabilities, valued "at prevailing selling prices". That is weaker than
  a firm order book. Score potential value at a haircut (50% by default) until purchase
  orders and revenue appear; track conversion every quarter.
- **Catching cyclical peaks.** Optical fibre is cyclical; STL itself boomed in 2018 and fell
  ~85% afterwards. Every early thesis needs a cycle check: margins and prices versus their
  10-year range, competitor capacity announcements, customer inventory.
- **Narrative stocks.** Press releases such as product launches carry no numbers. They must
  not move any score; only filings with quantities (value, capacity, price, customer) can.
- **Overtrading and friction.** Rs2,000 starters cost ~1–1.5% round trip in brokerage and DP
  charges, plus 20% short-term tax on gains. Cap open STARTERs at 4, require a 2-quarter
  time-stop (exit if no independent confirmation), and never open more than 2 new starters
  a month.
- **Adding because price rises.** Allowed only when a new independent fact arrives *and*
  expected value at the new price is still positive; a rising price alone never qualifies.
- **Confirmation bias.** Once a position exists, Stage 3 must be shown the previous thesis
  only after scoring the new evidence blind, and must restate the kill conditions first.
- **Data-mining the missed-winner database.** Studying only winners selects on the outcome.
  Every rule must be tested on matched non-winners from the same dates; without that the
  audit will "discover" rules that fire on half the market.
- **Look-ahead.** Yahoo dates quarters by period end, but results arrive 30–60 days later.
  Any backtest must key financials to the NSE results-filing timestamp. Filings must be
  dated by their dissemination time, not the event date.
- **Survivorship.** Audits must include stocks that exploded and then collapsed, and the
  universe must be point-in-time (names dropped from indices still count).
- **Entering too early.** "Approximately right early" is only valuable if small early bets
  are numerous enough to average out; with Rs10,000 a month, the system can carry only a few.
  Therefore the starter bar must still require one hard numeric fact.
- **Where I reject the framework:** (a) "Valuation before rerating" as a fixed 10 points —
  replace with a forward expected-value test, because a stock can look cheap on trailing
  numbers and still be priced for the contract; (b) the implied "80+ confirmation may be too
  late" heuristic — late is fine if forward expected value is still strong, as July showed for
  STL; (c) price moves as a scored signal — use them only to open research tickets.

## A. Keep from the September 29 system

- Deterministic Stage 1 over the whole universe, daily, with dated outputs.
- Operating-profit maths excluding other income; cash-flow forensics; governance vetoes.
- Industry-wide inflection (many peers improving at once) and score momentum.
- Evidence dossiers with NSE links; Claude underwriting on a small set; thesis history
  appended, never rewritten; capital ledger that only applies confirmed trades.
- Multibagger mathematics and "5×/10× not underwritable" honesty.

## B. Change

- Universe: all NSE equities with market cap ≥ Rs500 cr and 20-day turnover ≥ Rs1 cr
  (~1,800–2,000 names), refreshed monthly; keep names that leave (point-in-time).
- Add the deterministic early-inflection features and a filtered fast lane.
- Split scoring into Discovery, Confirmation, Valuation/EV, Risk and Action.
- Replace "buy only at 80+" with the state machine and staged sizing.
- Size orders against revenue; track conversion; haircut potential values.
- Add the missed-winner audit with control groups and a forward precision tracker per rule.

## C. Reject

- Scoring price momentum or "already moved" as positive evidence.
- Fixed valuation points instead of forward expected value.
- Unlimited starters or averaging down without new evidence.
- Learning rules from winners without matched non-winners.

## D. Final pipeline

1. **Universe** (monthly): NSE equity list + market cap + turnover filter, point-in-time log.
2. **Ingest** (daily, after close): prices, Yahoo fundamentals (weekly), every NSE filing with
   its dissemination timestamp, exchange surveillance notices.
3. **Stage 1 — deterministic features and scores** for every stock (E.1): Discovery-D
   (deterministic early score), Confirmation, Risk flags.
4. **Fast lane** (event-driven, same day): a filing that passes a materiality test (E.1) opens a
   RESEARCH ticket immediately, regardless of rank.
5. **Stage 2 — document extraction** (E.2) for: fast-lane tickets, the top 25 by Discovery-D,
   the top 25 by Confirmation and any stock whose Discovery-D rose ≥10 points in 20 sessions.
   Claude in a Claude Code session (or a regex/PDF parser where formats are standard) turns
   PDFs into numbers. Output: structured facts + dossier. Narrow to ≤10 weekly + all fast-lane.
6. **Stage 3 — underwriting** (Claude judgement, F/G): Discovery-J, Confirmation, EV,
   Risk, state transition, size, kill conditions, next datapoint.
7. **Ledger**: every state transition with price, date, evidence id; paper performance by
   state; forward precision per signal.
8. **Audit** (weekly): missed-winner detection and reconstruction (H); quarterly rule review (I).

## E. Features

### E.1 Stage 1 (deterministic, every stock, daily)

Confirmation (existing, fixed): revenue YoY and QoQ acceleration; core EBITDA (operating
income + depreciation) growth versus revenue; incremental EBITDA margin; core PBT growth;
other-income share; tax rate; CFO/PAT; receivable/inventory growth versus revenue; net
debt/EBITDA; interest cover; dilution; ROE/ROCE proxy; PEG; EPS growth minus price return.

Discovery-D (new):
- **Order intensity** = disclosed order/contract value in last 180 days ÷ TTM revenue
  (value from filing text or Stage 2 extraction; potential/allocation values at 50%).
- **Capacity intensity** = announced capacity increase % (or capex ÷ gross block) and
  commissioning within 2 quarters; utilization when disclosed.
- **Promoter conviction** = preferential issue/warrants to promoters: size ÷ market cap and
  issue price ÷ market price; promoter open-market buying; pledge release.
- **Margin inflection from a low base** = core EBITDA margin up ≥3 points QoQ while still
  below its 5-year median (early part of the move, not the peak).
- **Turnaround** = core profit positive after ≥2 negative quarters.
- **Rating momentum** = upgrade or outlook improvement, with rationale category.
- **Surveillance join** = NSE price-movement or volume-spurt query within ±3 sessions of a
  material filing (research trigger only; not a buying input).
- **Cycle position** (risk) = current margin percentile in the company's own 10-year range.

Fast-lane materiality tests (any one): order/contract ≥20% of TTM revenue; new
hyperscaler/global Tier-1 customer named or described; capacity ≥25% or capex ≥30% of gross
block; promoter preferential ≥3% of market cap at ≥90% of market price; core EBITDA margin
step-up ≥5 points QoQ; rating upgrade with business rationale; policy change explicitly
naming the company's product. Target volume: ≤5 tickets a week; thresholds tighten if more.

### E.2 Stage 2 (document extraction, facts only)

From result PDFs, presentations, call transcripts, order and capacity filings, rating
rationales: order value, tenure, firmness (firm PO / allocation / LOI), customer type and
geography; order-book total and book-to-bill; capacity, utilization, commissioning dates;
capex and funding; guidance numbers and changes versus last quarter; segment and geography
revenue; price/realization comments with numbers; customer concentration; working capital
days; debt targets. Each fact stored with source URL, page and FACT/MANAGEMENT CLAIM label.

### E.3 Stage 3 (judgement, Claude)

Is this day 1 of a multi-year change? Duration of shortage; competitor capacity response;
conversion probability of orders; realistic margin path; management credibility versus past
guidance; scenario probabilities; expected value; kill conditions; next datapoint.

## F. Scoring architecture (five outputs, never blended)

- **Discovery** (0–100): Discovery-D (deterministic, 60%) + Discovery-J (Claude, 40%).
  Weights from the owner's Early Inflection Score, with "valuation before rerating" moved out.
- **Confirmation** (0–100): the existing Sandisk score.
- **Valuation/EV**: probability-weighted 2-year return across bear/base/bull, and downside
  in the bear case. Example: 50% × +80%, 30% × +10%, 20% × −40% = +35% EV, −40% downside.
- **Risk**: governance, balance sheet, cycle position, liquidity, dilution, order firmness
  (each LOW/MEDIUM/HIGH; any HIGH governance = veto).
- **Action**: rule over the four (section G), with the evidence id that justified it.

## G. State machine and sizing (target position Rs10,000)

| State | Enter when | Size | Leave when |
|---|---|---|---|
| DISCOVER | Stage 1 or fast lane flags | 0 | Stage 2 done |
| RESEARCH | Discovery ≥60, or fast-lane ticket | 0 | Stage 3 decision within 10 sessions |
| STARTER | Discovery ≥70, one hard numeric fact, EV ≥ +30%, bear downside ≤ −35%, Risk no HIGH, open starters < 4 | Rs2,000–2,500 | 2-quarter time-stop without new independent fact |
| BUILD | New independent fact of a different kind (e.g. order then commissioning, or order then reported revenue) and EV at current price ≥ +25% | +Rs2,500–3,000 | Kill condition |
| CORE | Confirmation ≥75 with reported revenue/EBITDA and CFO/PAT ≥0.7, EV ≥ +20% | to Rs10,000 | — |
| HOLD | Thesis intact but EV < +20% at current price | no adds | EV turns negative or kill condition |
| TRIM | Price above bull-case value, or EV < 0 with thesis intact | sell 30–50% | — |
| EXIT | Kill condition, governance veto, or EV < 0 and Confirmation falling | sell all | Re-underwrite from zero before any re-entry |

Rules: no averaging down without a new fact; no add on price alone; max 2 new starters a
month; cash may accumulate indefinitely; holdings change only after confirmed execution.

## H. Missed-winner learning system

- **Detection** (weekly): stocks in the universe up ≥20% in 1 month, ≥40% in 3 months or ≥75%
  in 6 months, excluding moves explained only by index or sector beta (residual return).
- **Reconstruction** (point-in-time): rebuild what Stage 1/2 would have seen 30, 60, 90 and
  180 days before the move using filings by dissemination time, results by filing date and
  prices up to that day. Write the would-act decision before viewing later prices.
- **Record**: earliest detectable signal, best detection date and price, what the scanner saw,
  why it failed (not in universe / signal missing / signal below threshold / vetoed /
  Stage 3 declined), proposed rule, and whether the signal was genuinely predictive.
- **Control group**: for each proposed rule, all universe stocks where the rule would have
  fired in the same quarter; measure precision (share that then beat the market by X) and
  ticket volume. Store both winners and losers.
- **Adoption**: only if precision beats the current pipeline on controls from at least two
  different periods/sectors and ticket volume stays within budget. Adopted rules get a dated
  entry in a rule log and a forward tracker.
- **STL is case 1**: failure modes = not in universe; order size not measured; promoter
  warrants and surveillance flags not used; trailing-valuation bias in Stage 3.

## I. Anti-hindsight and false-positive validation

- Every rule pre-registered with its threshold and expected weekly volume before testing.
- Point-in-time data only; results keyed to filing timestamps.
- Matched controls for every rule; report precision, recall and volume, not anecdotes.
- Forward paper ledger of every state transition; monthly report of hit rate and return by
  state and by entry signal; rules retired automatically if forward precision falls below the
  baseline for two consecutive quarters.
- Research budget enforced (tickets per week); thresholds rise if exceeded, never fall to
  create activity.

## J. Worked example: STL under the v3 rules (honest, point-in-time)

**February** (not in your window, but the first real signal): the Feb 2–3 price queries plus
the Feb 7 promoter warrants (Rs498 cr at Rs110, ~10% of market cap) pass the fast-lane test
→ RESEARCH at ~Rs150. Stage 3 would likely stop there: losses in FY24–25, debt, and no
quantified demand yet. Promoter capital is a positive fact, but a struggling company raising
money is also consistent with balance-sheet repair. **Decision: RESEARCH, no starter.**
Catching Rs88–150 would require hindsight.

**April 20** (Neuralis US launch): press release without numbers → no score change.

**April 29** (Q4 FY26): revenue +37%, operating profit 2.6×, turnaround, FY26 margin 13.2%.
Confirmation ~60, Discovery ~65–70. Price ~Rs270–295 (market cap ~Rs14,000 cr ≈ 3× sales,
~22× FY26 EBITDA). EV on reported numbers alone is thin. **Decision: RESEARCH, high priority;
watch for quantified demand.**

**May 22** (USD 1.11 bn hyperscaler award ≈ 66% of FY26 revenue a year for three years,
haircut to 50% for allocation terms): fast lane fires. Base case CALCULATION with the
haircut: FY28 revenue ~Rs8,000–9,000 cr, EBITDA margin 16–18%, EPS ~Rs11–13 on ~56 cr shares
after warrants → ~34–40× at Rs441; bull (full conversion, 22% margin) EPS ~Rs20–22 → ~20–22×.
EV is positive but not huge; downside large if the award does not convert. **Decision:
STARTER Rs2,000–2,500 at ~Rs441**, kill conditions: no hyperscaler revenue visible by Q3 FY27;
fibre prices falling; capex funded by heavy debt.

**July 24** (Q1 FY27: revenue +87%, operating profit Rs300 cr, profit Rs197 cr): a new,
independent fact (reported revenue) of a different kind than the order → **BUILD +Rs3,000 at
~Rs540–560** if EV still ≥ +25%: run-rate EBITDA ~Rs1,500 cr annualized; FY28 EPS estimates move
to ~Rs18–21 → ~27× at Rs560. Confirmation ~75.

**August–October** (Aug 29 agreement, Sep 3 +50% capacity at ~Rs3,000 cr capex with 70%
utilization, Oct 1 USD 1.2 bn LTSA): order intensity rises and capacity confirms. But by
Rs900–955 the stock trades near ~38–45× the bull-case FY28 EPS. **Decision: HOLD (no add),
TRIM rule armed if price exceeds the bull-case value; capex funding and order conversion are
the main risks.**

**Result of the honest replay:** ~Rs5,000–5,500 deployed at an average ~Rs500, worth ~1.9×
at Rs955 — not the 11× from January, but early enough to make money and small enough at
entry to survive if the awards had not converted. That is the realistic target for v3.
