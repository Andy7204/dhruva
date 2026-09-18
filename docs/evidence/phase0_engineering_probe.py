"""Reproduce Phase 0 defects using temporary/in-memory fixtures only.

Run from any directory with Python 3.12+ and the project dependencies:
    python -B docs/evidence/phase0_engineering_probe.py

This is an audit of the original implementation, not an acceptance suite for
future fixes. A reproduced defect is reported explicitly as a defect. The only
repository write is the sibling phase0_engineering.json evidence file.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from qlab import data as D, livebook as LB, news, notify, orchestrator as O


def protected_hashes() -> dict[str, str]:
    """Cover all production code, state, reports and cache, not just Git status."""
    paths = [ROOT / name for name in (
        "config.json", "streamlit_app.py", "requirements.txt", "Dockerfile",
        "docker-compose.yml", ".gitignore", ".dockerignore",
    )]
    for name in ("qlab", "scripts", "runs", "reports", "data", ".github"):
        paths.extend(p for p in (ROOT / name).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts)
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file()}


def main() -> int:
    before = protected_hashes()
    cfg = D.load_config()
    checks = []

    def record(name, refs, observed, matched, defect=True):
        checks.append({"name": name, "references": refs, "observed": observed,
                       "expected_observation_reproduced": bool(matched),
                       "classification": "CONFIRMED_DEFECT" if defect else "VERIFIED_BEHAVIOR"})

    with tempfile.TemporaryDirectory(prefix="dhruva_phase0_engineering_") as tmp:
        root = Path(tmp)
        state = LB.new_livebook(cfg, "audit")
        state.update(processed_through="2026-09-14", as_of="2026-09-14",
                     inception="2026-09-14")
        (root / "livebook_audit.json").write_text(json.dumps(state), encoding="utf-8")
        visited = []

        def fake_step(book, panel, date, config, regime_ok, factor):
            visited.append(str(date.date()))
            book["as_of"] = str(date.date())

        cal = pd.bdate_range("2026-09-14", "2026-09-17")
        with patch.object(O, "RUNS", root), patch.object(O.LB, "step", fake_step), \
                patch.object(O.E, "_prices_at", return_value={}):
            O._run_livebook(cfg, "audit", {}, None, None, cal)
            first = list(visited)
            O._run_livebook(cfg, "audit", {}, None, None, cal)
        record("missed_sessions_not_recovered", ["qlab/orchestrator.py:34-43"],
               {"expected_sessions": ["2026-09-15", "2026-09-16", "2026-09-17"],
                "actual_sessions": first}, first == ["2026-09-17"])
        record("same_date_rerun_skips_engine_step", ["qlab/orchestrator.py:37-43"],
               {"additional_sessions": visited[len(first):]}, visited == first, defect=False)

    stale = pd.DataFrame({col: [1.] for col in D.OHLCV},
                         index=pd.to_datetime(["2020-01-01"]))
    logs = io.StringIO()
    with patch.object(D, "update_history", side_effect=RuntimeError("MOCK API unavailable")), \
            patch.object(D, "_read_cache", return_value=stale), contextlib.redirect_stdout(logs):
        returned = D.update_universe(["MOCK.NS"], pause=0)
    cutoff = str(returned["MOCK.NS"].index.max().date())
    record("failed_fetch_returns_stale_cache_as_data", ["qlab/data.py:157-170"],
           {"returned_date": cutoff, "console": logs.getvalue().strip()}, cutoff == "2020-01-01")

    with patch.dict(os.environ, {"TELEGRAM_TOKEN": "fake-token", "TELEGRAM_CHAT": "fake-chat"}), \
            patch("urllib.request.urlopen", side_effect=RuntimeError("MOCK HTTP failure")):
        sent = notify.send_telegram("Mock-only audit notification")
        item = news.check("MOCK.NS", pause=0)
    record("telegram_delivery_error_silently_false",
           ["qlab/notify.py:18-26", "qlab/orchestrator.py:101"],
           {"return_value": sent}, sent is False)
    record("news_failure_misclassified_quiet", ["qlab/news.py:45-69"],
           {"flag": item["flag"], "headlines": item["headlines"]},
           item["flag"] == "quiet" and item["headlines"] == [])

    state = LB.new_livebook(cfg, "audit")
    state["step_count"] = 1
    state["orders"] = [{"id": 1, "side": "BUY", "symbol": "OLD.NS", "kind": "cushion",
                        "status": "settled", "fill_date": "2026-09-14", "qty": 1, "amount": 100.}]
    LB.step(state, {}, pd.Timestamp("2026-09-17"), cfg, False, 1.)
    record("prior_settled_fill_removed", ["qlab/livebook.py:117-119", "qlab/report.py:315-321"],
           {"orders_after_next_session": state["orders"]}, state["orders"] == [])

    source = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="dhruva_phase0_streamlit_") as tmp:
        root = Path(tmp)
        (root / "runs").mkdir()
        (root / "reports").mkdir()
        (root / "runs/alert.txt").write_text("Dhruva - 2020-01-01: no action today", encoding="utf-8")
        (root / "runs/livebook_balanced.json").write_text(json.dumps(
            {"capital": 70000, "history": [["2020-01-01", 71000]]}), encoding="utf-8")
        (root / "runs/livebook_aggressive.json").write_text("MALFORMED JSON", encoding="utf-8")
        (root / "reports/dashboard.html").write_text("<h1>Old dashboard</h1>", encoding="utf-8")
        calls = []
        st = types.ModuleType("streamlit")
        components = types.ModuleType("streamlit.components")
        v1 = types.ModuleType("streamlit.components.v1")

        def capture(name):
            return lambda *args, **kwargs: calls.append((name, args))

        for name in ("set_page_config", "title", "info", "warning", "caption", "error", "metric"):
            setattr(st, name, capture(name))
        st.columns = lambda count: [st] * count
        v1.html = capture("html")
        components.v1 = v1
        st.components = components
        with patch.dict(sys.modules, {"streamlit": st, "streamlit.components": components,
                                      "streamlit.components.v1": v1}):
            exec(compile(source, "streamlit_app.py", "exec"),
                 {"__file__": str(root / "streamlit_app.py"), "__name__": "__main__"})
        warnings = [call for call in calls if call[0] in ("warning", "error")]
        metrics = [call for call in calls if call[0] == "metric"]
        rendered = any(call[0] == "html" for call in calls)
        record("stale_and_partial_books_render_without_warning",
               ["streamlit_app.py:19-41"],
               {"warnings": warnings, "metrics": metrics, "dashboard_rendered": rendered,
                "method": "Unmodified app source; only Streamlit calls and __file__ fixture path mocked."},
               warnings == [] and rendered and ("metric", ("Started with", "₹70,000")) in metrics)

    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    for script, label, refs in (
        ("scripts/show_call.py", "legacy_call_cli", ["scripts/show_call.py:16-21", "qlab/orchestrator.py:45-47"]),
        ("scripts/reset_book.py", "reset_dry_run", ["scripts/reset_book.py:12-25"]),
        ("research/test_challenge.py", "research_unit_tests", ["research/test_challenge.py:29-101"]),
    ):
        result = subprocess.run([sys.executable, "-B", str(ROOT / script)], cwd=ROOT,
                                env=env, text=True, encoding="utf-8", capture_output=True, timeout=60)
        record(label, refs, {"command": f"python -B {script}", "exit_code": result.returncode,
                            "stdout": result.stdout, "stderr": result.stderr},
               result.returncode == 0, defect=False)

    after = protected_hashes()
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    record("production_files_unchanged", ["docs/evidence/phase0_engineering_probe.py"],
           {"checked_files": len(before), "changed_files": changed}, not changed, defect=False)
    matched = all(check["expected_observation_reproduced"] for check in checks)
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Phase 0 audit observations; confirmed defects are not production acceptance passes.",
        "status": "AUDIT_OBSERVATIONS_REPRODUCED" if matched else "AUDIT_OBSERVATION_CHANGED",
        "runtime": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "safety": {"live_pipeline_run": False, "network_calls": False,
                   "fixtures": "temporary directories and in-memory only",
                   "production_unchanged": not changed},
        "source_hashes_sha256": {k: v for k, v in before.items()
                                  if k.startswith(("qlab/", "scripts/", ".github/"))
                                  or k in ("config.json", "streamlit_app.py", "requirements.txt")},
        "checks": checks,
    }
    destination = Path(__file__).with_name("phase0_engineering.json")
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{result['status']}: {len(checks)} observations; {len(before)} protected files; changed={changed}")
    print(destination)
    return 0 if matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
