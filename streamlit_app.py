"""Dhruva — public Streamlit dashboard.

Serves the daily-generated dashboard (reports/dashboard.html) plus the plain-text
call. A GitHub Actions cron regenerates the data every weekday evening and commits
it; Streamlit Community Cloud redeploys automatically, so this stays live with no
manual step. Deploy: point Streamlit Cloud at this file. See DEPLOY.md.
"""
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Dhruva", page_icon="🪷", layout="wide")

st.title("Dhruva · your steadfast momentum engine")

alert = ROOT / "runs" / "alert.txt"
if alert.exists():
    st.info("**Today's call**\n\n" + alert.read_text(encoding="utf-8"))

# headline numbers from the live books
tot, start = 0.0, 0.0
for f in (ROOT / "runs").glob("livebook_*.json"):
    try:
        s = json.loads(f.read_text())
        hist = s.get("history", [])
        tot += hist[-1][1] if hist else s.get("capital", 0)
        start += s.get("capital", 0)
    except Exception:
        pass
if start:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total value", f"₹{tot:,.0f}")
    c2.metric("Return", f"{(tot/start-1)*100:+.1f}%")
    c3.metric("Started with", f"₹{start:,.0f}")

dash = ROOT / "reports" / "dashboard.html"
if dash.exists():
    components.html(dash.read_text(encoding="utf-8"), height=3200, scrolling=True)
else:
    st.warning("No dashboard generated yet — the daily job will create it on its first run.")

st.caption("Research & educational paper trading — not investment advice. Auto-updates each weekday "
           "evening (IST) via GitHub Actions. Decisions & risk are yours.")
