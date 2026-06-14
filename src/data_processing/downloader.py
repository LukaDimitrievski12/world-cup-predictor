"""
Dataset download helper for the World Cup Predictor project.

Provides:
1. Human-readable instructions for manual download.
2. Automated download via the Kaggle API (requires credentials).

Setup (one-time)
----------------
1. pip install kaggle
2. Create an API token at https://www.kaggle.com/settings → API → Create New Token
3. Place kaggle.json in:
      Windows : C:\\Users\\<you>\\.kaggle\\kaggle.json
      Mac/Linux: ~/.kaggle/kaggle.json
4. The file should contain:  {"username": "...", "key": "..."}

Usage
-----
    python -m src.data_processing.downloader          # interactive
    python -m src.data_processing.downloader --auto   # skip prompt
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR: Path = _PROJECT_ROOT / "data" / "raw"

# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------

DATASETS: dict[str, dict] = {
    "match_results": {
        "description": "International football results 1872–present (Mart Jürisoo)",
        "kaggle_id": "martj42/international-football-results-from-1872-to-2024",
        "files": ["results.csv", "goalscorers.csv", "shootouts.csv"],
        "manual_url": (
            "https://www.kaggle.com/datasets/martj42/"
            "international-football-results-from-1872-to-2024"
        ),
    },
    "fifa_rankings": {
        "description": "FIFA World Rankings 1992–2024 (cashncarry)",
        "kaggle_id": "cashncarry/fifaworldranking",
        "files": ["fifa_ranking-2023-07-20.csv"],
        "manual_url": "https://www.kaggle.com/datasets/cashncarry/fifaworldranking",
    },
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def print_instructions() -> None:
    """Print manual download instructions for all datasets."""
    sep = "=" * 64
    print(f"\n{sep}")
    print("  DATASET DOWNLOAD GUIDE")
    print(sep)
    for name, info in DATASETS.items():
        print(f"\n[{name.upper()}]")
        print(f"  {info['description']}")
        print(f"  URL   : {info['manual_url']}")
        print(f"  Files : {', '.join(info['files'])}")
    print(f"\n  Save all files to: {RAW_DIR}\n{sep}\n")


def download_all(confirm: bool = True) -> None:
    """
    Download all datasets via the Kaggle CLI.

    Parameters
    ----------
    confirm : bool
        When True, prompt the user before proceeding.
    """
    if confirm:
        answer = input("Download datasets via Kaggle CLI? [y/N]: ").strip().lower()
        if answer != "y":
            print("Skipped. Use manual download instructions above.")
            return

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for name, info in DATASETS.items():
        logger.info("Downloading '%s' …", info["description"])
        cmd = [
            sys.executable, "-m", "kaggle",
            "datasets", "download",
            "-d", info["kaggle_id"],
            "-p", str(RAW_DIR),
            "--unzip",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(
                "Download failed for '%s':\n%s\n"
                "Check your Kaggle credentials or download manually from:\n%s",
                name,
                result.stderr.strip(),
                info["manual_url"],
            )
        else:
            logger.info("'%s' downloaded successfully.", name)


def verify_downloads() -> dict[str, bool]:
    """
    Check which expected files are present in ``data/raw/``.

    Returns
    -------
    dict[str, bool]
        Maps each expected filename to True/False.
    """
    status: dict[str, bool] = {}
    for info in DATASETS.values():
        for fname in info["files"]:
            present = (RAW_DIR / fname).exists()
            status[fname] = present
            icon = "✓" if present else "✗"
            print(f"  {icon}  {fname}")
    return status


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download World Cup Predictor datasets from Kaggle."
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Download without prompting (non-interactive).",
    )
    return parser.parse_args()


def main() -> None:
    print_instructions()
    print("Checking existing downloads …")
    verify_downloads()
    args = _parse_args()
    download_all(confirm=not args.auto)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    main()
