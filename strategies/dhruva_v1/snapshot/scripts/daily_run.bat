@echo off
REM Daily momentum-trader update — run after the NSE close on trading days.
REM Refreshes data, advances the paper book, writes runs\todays_call.json + reports\dashboard.html
cd /d "%~dp0.."
"C:\Program Files\Python314\python.exe" scripts\daily_run.py >> runs\daily_run.log 2>&1
