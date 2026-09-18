"""Bounded Phase 0 audit probes; only this evidence JSON may be written.

Run from any directory with Python and the existing pandas/numpy dependencies:
    python -B docs/evidence/phase0_quant_probe.py

These are diagnostic reproductions of the original engine, not assertions that
its behavior is correct. Synthetic fixtures stay in memory; the orchestrator
probe redirects RUNS to an automatically removed temporary directory. No market
data is fetched and no production pipeline is invoked. Existing research unit
tests run without bytecode writes. Production-file hashes are compared before
and after. A later corrected implementation may intentionally change results.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "docs/evidence/phase0_quant.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def production_fingerprints() -> dict[str, str]:
    files = [ROOT / p for p in ("config.json", "streamlit_app.py", "README.md", "AGENTS.md")]
    for dirname in ("qlab", "runs", "data", "reports", ".github", "scripts", "research"):
        files.extend(p for p in (ROOT / dirname).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts)
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(set(files)) if p.is_file()}


def main() -> None:
    before = production_fingerprints()
    import pandas as pd
    from qlab import data as D, indicators as I, livebook as L, engine as E
    from qlab import orchestrator as O, tax as T

    cfg = D.load_config()
    findings = []

    def record(identifier, title, observed, reproduced, refs):
        findings.append({"id": identifier, "title": title, "observed": observed,
                         "reproduced": bool(reproduced), "file_line_references": refs})

    idx = pd.bdate_range("2026-01-01", periods=5)
    prices = pd.DataFrame({"close": [100, 100, 200, 200, 200],
                           "adjclose": [100, 100, 200, 200, 200]}, index=idx)
    prefix_kept = idx[2] in D.clean_ohlc(prices.iloc[:3]).index
    full_kept = idx[2] in D.clean_ohlc(prices).index
    record("centered_cleaning", "Future rows change past row inclusion",
           {"prefix_keeps_third_row": prefix_kept, "full_keeps_third_row": full_kept},
           not prefix_kept and full_kept, ["qlab/data.py:99"])

    idx20 = pd.bdate_range("2026-01-01", periods=20)
    raw = pd.DataFrame({"open": 100., "high": 102., "low": 98., "close": 100.,
                        "adjclose": 50., "volume": 100000.}, index=idx20)
    enriched = I.enrich(raw)
    adjusted = raw.copy()
    adjusted[["open", "high", "low", "close"]] *= .5
    actual_atr, adjusted_atr = float(enriched.atr14.iloc[-1]), float(I.atr(adjusted).iloc[-1])
    record("atr_units", "Raw ATR is mixed with adjusted prices",
           {"production_atr": actual_atr, "adjusted_atr": adjusted_atr},
           actual_atr == 4 and adjusted_atr == 2,
           ["qlab/indicators.py:90", "qlab/indicators.py:105", "qlab/livebook.py:184"])

    c = copy.deepcopy(cfg)
    c["slippage_bps"] = 0
    c["defensive_basket"] = {}
    c["allocation"]["mode"] = "fixed"
    c["risk"]["circuit_breaker_dd"] = 0
    for key, value in c["costs"].items():
        if isinstance(value, (int, float)):
            c["costs"][key] = 0
    cal = pd.bdate_range("2026-01-05", periods=3)
    panel = {"TEST.NS": pd.DataFrame({
        "adj_open": [100., 80., 100.], "adj_low": [100., 75., 100.],
        "adjclose": [100., 80., 100.], "adj_high": [100., 85., 100.]}, index=cal)}

    def state():
        s = L.new_livebook(c, "test")
        s.update(step_count=1, inception=str(cal[0].date()))
        return s

    s = state()
    s["cash"] = 99000.
    s["holdings"] = {"TEST.NS": {"qty": 10, "avg": 100., "cost": 1000.,
        "kind": "stock", "stop": 90., "acquired": str(cal[0].date())}}
    L.step(s, panel, cal[1], c, False, .4)
    fill = s["orders"][0]["fill_price"]
    record("gap_stop", "Stop fills above the entire session price range",
           {"sale_price": fill, "session_open": 80., "session_high": 85., "stop": 90.},
           fill > 85, ["qlab/livebook.py:125", "qlab/livebook.py:127", "qlab/engine.py:274"])

    s = state()
    s["cash"] = 0.
    s["holdings"] = {"TEST.NS": {"qty": 1000, "avg": 100., "cost": 100000.,
        "kind": "stock", "stop": 0., "acquired": str(cal[0].date())}}
    s["orders"] = [
        {"id": 1, "status": "scheduled", "side": "SELL", "symbol": "TEST.NS", "kind": "stock"},
        {"id": 2, "status": "scheduled", "side": "BUY", "symbol": "TEST.NS", "kind": "stock",
         "target_value": 100000.}]
    L.step(s, panel, cal[2], c, False, .4)
    bought = s["holdings"]["TEST.NS"]["qty"]
    record("settlement_cash", "Same-session proceeds fund a new purchase",
           {"opening_cash": 0., "same_session_shares_bought": bought, "settle_days": 1},
           bought == 990, ["qlab/livebook.py:72", "qlab/livebook.py:97", "qlab/livebook.py:111"])

    s = state()
    s["realized_sales"] = [{"symbol": "TEST.NS", "exit_date": "2026-01-05",
                             "holding_days": 10, "gain": 10000.}]
    L.step(s, panel, cal[2], c, False, .4)
    record("tax_nav", "Accrued tax is not reserved or deducted from reported NAV",
           {"tax_accrued": s["tax_accrued"], "cash": s["cash"], "nav": s["history"][-1][1]},
           s["tax_accrued"] == 2000 and s["cash"] == s["history"][-1][1] == 100000,
           ["qlab/livebook.py:39", "qlab/livebook.py:203", "qlab/report.py:230", "qlab/report.py:344"])

    with tempfile.TemporaryDirectory(prefix="dhruva_phase0_") as tmp:
        original_runs = O.RUNS
        O.RUNS = Path(tmp)
        try:
            s = state()
            dstr = str(cal[0].date())
            s.update(processed_through=dstr, as_of=dstr, history=[[dstr, 100000.]])
            (O.RUNS / "livebook_test.json").write_text(json.dumps(s), encoding="utf-8")
            result = O._run_livebook(c, "test", panel, None, None, list(cal))
            actual_dates = [r[0] for r in result["state"]["history"]]
        finally:
            O.RUNS = original_runs
    record("missed_session_recovery", "Recovery skips the intermediate unprocessed session",
           {"available_dates": [str(d.date()) for d in cal], "actual_history_dates": actual_dates},
           actual_dates == ["2026-01-05", "2026-01-07"], ["qlab/orchestrator.py:34", "qlab/orchestrator.py:38"])

    sales = [{"symbol": "TEST.NS", "exit_date": "2026-09-17", "holding_days": 400, "gain": 100000.}]
    separate, shared = 2 * T.accrued_tax(sales, c)[0], T.accrued_tax(sales * 2, c)[0]
    record("shared_tax_account", "Separate book calls duplicate the configured annual exemption",
           {"separate_books_tax": separate, "shared_account_tax": shared},
           separate == 0 and shared == 9375, ["qlab/tax.py:45", "qlab/livebook.py:203", "qlab/orchestrator.py:71"])

    defensive_panel = {"GOLDBEES.NS": pd.DataFrame({"mom_score": [100.], "turnover": [1e9]}, index=[cal[-1]])}
    top = E._momentum_top_set(defensive_panel, cal[-1], 15, c)
    record("aggressive_defensive_universe", "Empty basket override admits a defensive ETF as momentum stock",
           {"selected": top}, "GOLDBEES.NS" in top,
           ["qlab/engine.py:163", "qlab/engine.py:170", "qlab/orchestrator.py:72"])

    missing_error = None
    try:
        E._get(None, cal[-1], "adj_low")
    except Exception as exc:
        missing_error = f"{type(exc).__name__}: {exc}"
    record("missing_held_symbol", "Missing held-symbol frame can crash the stop lookup",
           {"exception": missing_error}, missing_error == "AttributeError: 'NoneType' object has no attribute 'at'",
           ["qlab/livebook.py:125", "qlab/engine.py:102"])

    cache = {"configured_universe_count": len(cfg["universe"]), "missing": [], "short_history": [],
             "duplicate_dates": {}, "invalid_ohlc": {}, "non_daily": {}, "last_dates": {},
             "zero_volume_any_rows_symbols": [], "zero_volume_latest_symbols": []}
    for symbol in cfg["universe"] + [cfg["regime"]["benchmark"]]:
        path = D._cache_path(symbol)
        if not path.exists():
            cache["missing"].append(symbol)
            continue
        frame = pd.read_csv(path, index_col="date", parse_dates=["date"])
        if len(frame) < 260:
            cache["short_history"].append({"symbol": symbol, "rows": len(frame)})
        duplicates = int(frame.index.duplicated().sum())
        if duplicates:
            cache["duplicate_dates"][symbol] = duplicates
        price_cols = frame[["open", "high", "low", "close", "adjclose"]]
        invalid = ((price_cols <= 0).any(axis=1) | price_cols.isna().any(axis=1)
                   | (frame.high < frame[["open", "close", "low"]].max(axis=1))
                   | (frame.low > frame[["open", "close", "high"]].min(axis=1)))
        if invalid.sum():
            cache["invalid_ohlc"][symbol] = int(invalid.sum())
        zeros = (frame.volume <= 0) | frame.volume.isna()
        if zeros.any():
            cache["zero_volume_any_rows_symbols"].append(symbol)
        if zeros.iloc[-1]:
            cache["zero_volume_latest_symbols"].append(symbol)
        cache["last_dates"][symbol] = str(frame.index.max().date())
        if len(frame) > 3 and frame.index.to_series().diff().median().days > 5:
            cache["non_daily"][symbol] = str(frame.index.to_series().diff().median())
    cache["last_date_counts"] = dict(Counter(cache["last_dates"].values()))

    manifest = json.loads((ROOT / "research/results/manifest.json").read_text(encoding="utf-8"))
    verification = json.loads((ROOT / "research/results/verification.json").read_text(encoding="utf-8"))
    data_hash_matches = {s: D._cache_path(s).exists() and digest(D._cache_path(s)) == info["sha256"]
                         for s, info in manifest["data_audit"].items() if "sha256" in info}
    source_hash_matches = {p: digest(ROOT / p) == h for p, h in verification["sources_sha256"].items()}
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
    tests = subprocess.run([sys.executable, "-B", str(ROOT / "research/test_challenge.py")],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    after = production_fingerprints()
    changed = [p for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)]
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only Phase 0 diagnostic evidence; synthetic fixtures are not market performance results.",
        "runtime": {"python": sys.version, "executable": sys.executable, "pandas": pd.__version__},
        "findings": findings, "all_nine_preexisting_defects_reproduced": all(f["reproduced"] for f in findings),
        "cache_audit": cache,
        "research_reproducibility": {
            "source_hash_matches": source_hash_matches,
            "config_hash_matches": digest(ROOT / "config.json") == manifest["config_sha256"],
            "protocol_hash_matches": digest(ROOT / "research/PROTOCOL.md") == manifest["protocol_sha256"],
            "data_hash_match_count": sum(data_hash_matches.values()),
            "data_hash_total": len(data_hash_matches),
            "changed_data_symbols": [s for s, matches in data_hash_matches.items() if not matches],
            "caveat": "Hash mismatch proves changed files, not necessarily changed historical rows. Pin/reconstruct original inputs for exact reruns."},
        "research_unit_tests": {"command": "python -B research/test_challenge.py", "exit_code": tests.returncode,
                                 "output": tests.stdout + tests.stderr,
                                 "scope": "These eight tests validate the isolated research engine, not production."},
        "production_unchanged": not changed, "production_files_compared": len(before), "changed_production_paths": changed,
        "audited_source_sha256": {p: before[p] for p in before if p.startswith("qlab/") or p == "config.json"},
    }
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(OUTPUT), "defects_reproduced": sum(f["reproduced"] for f in findings),
                      "research_tests_exit_code": tests.returncode, "production_unchanged": not changed,
                      "production_files_compared": len(before),
                      "research_data_hash_matches": f"{sum(data_hash_matches.values())}/{len(data_hash_matches)}"}, indent=2))
    if changed or tests.returncode or not all(f["reproduced"] for f in findings):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
