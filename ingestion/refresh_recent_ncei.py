"""Discover and download the newest official NCEI Storm Events files for recent years."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

INDEX_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
BASELINE_END_YEAR = 2024


def latest_filename(index: str, year: int) -> str | None:
    """Return the newest NCEI details filename for year, or None if NCEI hasn't published one yet.

    Callers decide whether a missing file is expected (the current calendar
    year, which NCEI typically doesn't publish until days to weeks in) or an
    error (any past year, where a miss likely means the index format changed
    or a real file is missing).
    """
    pattern = re.compile(rf"StormEvents_details-ftp_v1\.0_d{year}_c\d{{8}}\.csv\.gz")
    matches = sorted(set(pattern.findall(index)))
    return matches[-1] if matches else None


def main() -> None:
    parser = argparse.ArgumentParser()
    current_year = datetime.now(timezone.utc).year
    parser.add_argument(
        "--years", nargs="+", type=int,
        default=list(range(BASELINE_END_YEAR + 1, current_year + 1)),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/ncei-storm-events"))
    args = parser.parse_args()

    index_response = requests.get(INDEX_URL, timeout=60)
    index_response.raise_for_status()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for year in args.years:
        filename = latest_filename(index_response.text, year)
        if filename is None:
            if year >= current_year:
                print(f"No NCEI bulk file published yet for {year}; skipping this run.")
                continue
            raise RuntimeError(f"No NCEI bulk file found for {year}")
        destination = args.output_dir / filename
        response = requests.get(f"{INDEX_URL}{filename}", stream=True, timeout=120)
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
        print(destination)


if __name__ == "__main__":
    main()
