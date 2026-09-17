"""Package Dhruva into ONE zip you can send to another device or push to GitHub.

    python scripts/package.py            -> dist/dhruva.zip  (full, includes price cache)
    python scripts/package.py --slim     -> dist/dhruva-slim.zip (no cache; fetched on first run)

The full zip is self-contained: unzip and `docker compose up dhruva` shows the
dashboard immediately, offline. The slim zip is tiny but fetches prices on the
first `update` run (needs internet). Junk (__pycache__/.git/.pyc) is always skipped.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"__pycache__", ".git", ".github", ".pytest_cache", "dist", "scratchpad"}
SKIP_EXT = {".pyc", ".pyo"}
SKIP_NAMES = {".DS_Store"}


def main() -> None:
    slim = "--slim" in sys.argv
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / ("dhruva-slim.zip" if slim else "dhruva.zip")
    if out.exists():
        out.unlink()

    n, total = 0, 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT)
            parts = set(rel.parts)
            if parts & SKIP_DIRS or p.name in SKIP_NAMES or p.suffix in SKIP_EXT:
                continue
            if slim and rel.parts[:2] == ("data", "cache"):
                continue  # slim build: drop the price cache
            if p.is_file():
                z.write(p, Path("dhruva") / rel)  # everything under a top-level dhruva/ folder
                n += 1
                total += p.stat().st_size

    mb = out.stat().st_size / 1e6
    print(f"Wrote {out}")
    print(f"  {n} files, {total/1e6:.0f} MB uncompressed -> {mb:.0f} MB zipped"
          f"{' (slim, no price cache)' if slim else ''}")
    print("\nOn the other device: unzip, then either")
    print("  docker compose up dhruva      # view at http://localhost:8501")
    print("  docker compose run --rm update  # refresh the data")


if __name__ == "__main__":
    main()
