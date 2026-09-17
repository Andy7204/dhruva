# Deploy Dhruva as an autonomous public dashboard

Goal: a public link that shows the dashboard and **updates itself every weekday
evening** with no manual step. Free, using **GitHub Actions** (the scheduler) +
**Streamlit Community Cloud** (the public page).

> ⚠️ Research/paper-trading only — not investment advice. No real orders are placed.

## 1. Put this folder in its own GitHub repo
Use `dhruva/` as the **repo root**, with `streamlit_app.py` directly at the root.

```bash
cd dhruva
git init && git add -A && git commit -m "Dhruva"
gh repo create dhruva --public --source=. --push   # or create the repo on github.com and push
```

Commit the pre-built evidence files too so the page has history on day one:
`runs/backtest_comparison.json`, `runs/validation.json`, `reports/dashboard.html`.
(Commit `data/cache/` so the first cron run is fast; otherwise the
first run re-downloads ~5 years and takes ~15 min, then the cache keeps it fast.)

## 2. The scheduler is already set up
`.github/workflows/daily.yml` runs **weekdays 13:00 UTC (18:30 IST)**: it fetches
the latest prices, advances the live book (fills yesterday's scheduled orders at
today's open, settles, schedules new ones), rebuilds `reports/dashboard.html`,
and commits it back. Enable it: repo → **Actions** tab → enable workflows. Test it
now with **Run workflow** (workflow_dispatch).

**Optional phone alerts (Telegram):** create a bot via @BotFather, get your chat id,
then repo → Settings → Secrets → Actions → add `TELEGRAM_TOKEN` and `TELEGRAM_CHAT`.
The job will message you the day's orders.

**Optional LLM narration without an OpenAI key:** add `ANTHROPIC_API_KEY` as an
Actions repository secret. The workflow passes it to the existing Anthropic
narrator. `OPENAI_API_KEY` is an alternative, not a requirement. With neither key,
the built-in rule-based narrator runs; API failures also fall back to that writer.
The LLM only rephrases facts and cannot change trading decisions.

Secrets belong under **Settings → Secrets and variables → Actions → New repository
secret**. Never commit secret values. GitHub supplies `GITHUB_TOKEN` automatically;
the workflow requests `contents: write` to commit generated output. The weekday
13:00 UTC schedule corresponds to 18:30 IST; scheduled jobs may start late.

## 3. Publish the page (Streamlit Community Cloud — free)
1. Go to https://share.streamlit.io → **New app**.
2. Pick your `dhruva` repo, branch `main`, main file `streamlit_app.py`.
3. Deploy. You get a public URL like `https://dhruva.streamlit.app`.

Streamlit Cloud watches the repo, so each daily commit from the cron **auto-redeploys**
the page with fresh numbers. That's the whole loop — no manual updates.

## Alternative (simpler, no interactivity): GitHub Pages
Skip Streamlit; add a step to the workflow that copies `reports/dashboard.html` to
`index.html` and enable **Pages** on the repo. The cron then publishes the static
dashboard to `https://<you>.github.io/dhruva/`.

## Notes
- The cron needs internet (GitHub runners have it) — it fetches from Yahoo Finance.
- Keep the repo **public** for free Streamlit/Pages hosting; it contains no secrets
  (Telegram token lives in encrypted Actions secrets, never in the code).
- To change the split, capital, or strategy, edit `config.json` and push.
