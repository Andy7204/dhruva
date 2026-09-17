"""Run the daily paper-trading step. Usage:
    python scripts/daily_run.py            # refresh data, advance the book
    python scripts/daily_run.py --no-refresh   # use cached data (fast)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qlab.orchestrator import daily_run  # noqa: E402

if __name__ == "__main__":
    daily_run(refresh="--no-refresh" not in sys.argv)
