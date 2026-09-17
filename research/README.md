# Isolated challenge study

Read `PROTOCOL.md` first. The ten main variants were specified before running the
comparison. `same_asset.py` is a separately labeled supplemental control added
after viewing that matrix to isolate ETF timing from stock selection.

```powershell
python -m pip install -r research/requirements.txt
python research/test_challenge.py
python research/challenge.py
python research/scenarios.py
python research/same_asset.py
python research/verify_results.py
python research/make_report.py
```

Open `results/REPORT.html` for the full standalone report. It embeds both charts
and includes each argument, full results, robustness checks and assumptions.
`results/REPORT.md` is a text summary. `results/results.json`, `same_asset.json`,
`synthetic.json`, `curves.csv`, and `trades_*.csv` hold reproducible evidence.
`manifest.json` records source cache hashes and coverage; `verification.json`
records source-code hashes and independent ledger reconciliation.

All prices are read from the supplied cache; nothing is downloaded. No production
configuration, code, live book, dashboard, or price cache is written. The main
study uses the common complete coverage through 2026-09-15 and starts after
260 benchmark sessions on 2022-10-03. The final-year check uses a new account
starting in cash and past observations for warmup. It is not a truly untouched
holdout because original strategy development already used this history.

This is a policy comparison with an audited research execution model, not an
exact replay of the deployed app. It corrects specific accounting/execution
problems documented in the protocol. Tax and distributions remain approximations,
and today's constituents remain survivorship-biased even for the Nifty-100 check.

No rule has been selected for deployment based on this study.
