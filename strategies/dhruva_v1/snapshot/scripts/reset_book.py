"""Reset the paper book (state, journal, learned weights).

    python scripts/reset_book.py          # dry run — shows what would be removed
    python scripts/reset_book.py --yes    # actually remove them

Cached market data under data/cache/ is NOT touched.
"""
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "runs"
TARGETS = ["state.json", "journal.jsonl", "weights.json"]

if __name__ == "__main__":
    do = "--yes" in sys.argv
    for name in TARGETS:
        p = RUNS / name
        if p.exists():
            print(("removing " if do else "would remove ") + str(p))
            if do:
                p.unlink()
        else:
            print("absent    " + str(p))
    if not do:
        print("\nDry run. Re-run with --yes to actually reset the book.")
