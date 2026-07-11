"""Build a compact, reproducible NCEI historical tornado baseline for this project."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from load_ncei_events import COHORT_STATES, STATE_NAME_TO_CODE
from refresh_recent_ncei import INDEX_URL, latest_filename

OUTPUT_FIELDS = [
    "EVENT_ID", "EVENT_TYPE", "STATE", "CZ_NAME", "BEGIN_DATE_TIME", "CZ_TIMEZONE", "BEGIN_LOCATION", "END_LOCATION",
    "TOR_F_SCALE", "TOR_LENGTH", "TOR_WIDTH", "BEGIN_LAT", "BEGIN_LON", "END_LAT", "END_LON",
    "INJURIES_DIRECT", "DEATHS_DIRECT", "DAMAGE_PROPERTY", "DAMAGE_CROPS", "EVENT_NARRATIVE",
]


def value(row: dict[str, str], key: str) -> str:
    return row.get(key) or row.get(key.lower()) or ""


def state_code(row: dict[str, str]) -> str:
    state = value(row, "STATE").upper()
    return STATE_NAME_TO_CODE.get(state, state)


def write_filtered_year(
    destination: csv.DictWriter,
    filename: str,
    session: requests.Session,
) -> int:
    response = session.get(f"{INDEX_URL}{filename}", stream=True, timeout=180)
    response.raise_for_status()
    response.raw.decode_content = False
    retained = 0

    with gzip.GzipFile(fileobj=response.raw) as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8", errors="replace", newline="") as source:
            for row in csv.DictReader(source):
                if value(row, "EVENT_TYPE") != "Tornado" or state_code(row) not in COHORT_STATES:
                    continue
                destination.writerow({field: value(row, field) for field in OUTPUT_FIELDS})
                retained += 1
    response.close()
    return retained


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and filter NCEI details files into a committed 1950-2024 project baseline.",
    )
    parser.add_argument("--start-year", type=int, default=1950)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("data/StormEvents_details.csv.gz"))
    parser.add_argument("--metadata-output", type=Path, default=Path("data/historical_baseline_metadata.json"))
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append a non-overlapping year range to an existing baseline and update its metadata.",
    )
    args = parser.parse_args()
    if args.start_year > args.end_year:
        raise ValueError("--start-year must be less than or equal to --end-year")

    session = requests.Session()
    index_response = session.get(INDEX_URL, timeout=60)
    index_response.raise_for_status()
    index = index_response.text
    years = list(range(args.start_year, args.end_year + 1))
    filenames = []
    for year in years:
        filename = latest_filename(index, year)
        if filename is None:
            raise RuntimeError(f"No NCEI bulk file found for {year}")
        filenames.append(filename)

    if args.append and not args.output.exists():
        raise FileNotFoundError("--append requires an existing --output baseline")
    if args.append and not args.metadata_output.exists():
        raise FileNotFoundError("--append requires existing baseline metadata")

    existing_metadata: dict = {}
    if args.append:
        existing_metadata = json.loads(args.metadata_output.read_text(encoding="utf-8"))
    existing_years = existing_metadata.get("years", [])
    if set(existing_years).intersection(years):
        raise ValueError("--append year range overlaps existing baseline metadata")
    existing_filenames = existing_metadata.get("filenames", [])
    existing_by_year = existing_metadata.get("eventsByYear", {})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=args.output.parent,
        prefix=f".{args.output.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    retained_by_year: dict[int, int] = {}
    try:
        with gzip.open(temporary_path, "wt", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS)
            if not args.append:
                writer.writeheader()
            for year, filename in zip(years, filenames, strict=True):
                retained_by_year[year] = write_filtered_year(writer, filename, session)
                print(f"{year}: retained {retained_by_year[year]} cohort tornado events")
        if args.append:
            with args.output.open("ab") as baseline, temporary_path.open("rb") as addition:
                shutil.copyfileobj(addition, baseline)
        else:
            temporary_path.replace(args.output)
    finally:
        temporary_path.unlink(missing_ok=True)
        session.close()

    metadata = {
        "source": "NOAA NCEI Storm Events bulk details files",
        "sourceIndex": INDEX_URL,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "years": sorted([*existing_years, *years]),
        "filenames": [*existing_filenames, *filenames],
        "eventCount": existing_metadata.get("eventCount", 0) + sum(retained_by_year.values()),
        "eventsByYear": {**existing_by_year, **retained_by_year},
        "filter": "EVENT_TYPE = Tornado and state in the documented 13-state project cohorts",
    }
    args.metadata_output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {metadata['eventCount']} events to {args.output}")


if __name__ == "__main__":
    main()
