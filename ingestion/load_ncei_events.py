"""Load a filtered NCEI Storm Events CSV or CSV.GZ into DuckDB."""

from __future__ import annotations

import argparse
import csv
import gzip
import os
import re
from datetime import datetime
from pathlib import Path

import duckdb

COHORT_STATES = {"AL", "AR", "GA", "LA", "MS", "TN", "CO", "IA", "KS", "NE", "OK", "SD", "TX"}
STATE_NAME_TO_CODE = {
    "ALABAMA": "AL", "ARKANSAS": "AR", "GEORGIA": "GA", "LOUISIANA": "LA", "MISSISSIPPI": "MS", "TENNESSEE": "TN",
    "COLORADO": "CO", "IOWA": "IA", "KANSAS": "KS", "NEBRASKA": "NE", "OKLAHOMA": "OK", "SOUTH DAKOTA": "SD", "TEXAS": "TX",
}

# NCEI CZ_TIMEZONE values take two observed forms across the 1950-2024 baseline:
# a modern explicit-offset form ("CST-6", "EST-5", "MST-7", ...) and an older
# bare zone-abbreviation form used in early Storm Events years ("CST", "EST",
# "PST", ...) with no digit. Verified against real NCEI files: 2023 uses the
# "-N" suffix form for the large majority of rows; 1955 uses the bare
# abbreviation form exclusively. Most rows hold the zone to its fixed
# standard-time offset regardless of event date, but a full pass over the
# committed 1950-2024 baseline (46,246 rows) also found a small number of
# rows (about 0.2%) using daylight-time-labeled bare abbreviations (CDT, EDT,
# MDT), so those are mapped to their correct (not standard-time) offset
# rather than being treated as unrecognized.
CZ_TIMEZONE_ABBREVIATION_OFFSETS = {
    "CST": "-06:00",
    "CDT": "-05:00",
    "EST": "-05:00",
    "EDT": "-04:00",
    "MST": "-07:00",
    "MDT": "-06:00",
    "PST": "-08:00",
    "PDT": "-07:00",
    "AST": "-04:00",
    "AKST": "-09:00",
    "HST": "-10:00",
}
# CST is the modal timezone across this project's cohort states (roughly
# three-quarters of cohort-state tornado rows in a 2023 sample, effectively
# all of them in older years), so it is the sensible default for any
# CZ_TIMEZONE value this project doesn't recognize (observed in the baseline:
# a handful of UNK, GMT, and apparent data-entry typos, well under 0.1% of rows).
DEFAULT_CZ_TIMEZONE_OFFSET = "-06:00"
_CZ_TIMEZONE_OFFSET_PATTERN = re.compile(r"^[A-Z]+([+-])(\d{1,2})$")


def parse_cz_timezone_offset(value: str | None) -> str:
    """Turn an NCEI CZ_TIMEZONE value into a +HH:MM/-HH:MM UTC offset suffix.

    Falls back to DEFAULT_CZ_TIMEZONE_OFFSET for missing or unrecognized values.
    """
    if value:
        normalized = value.strip().upper()
        match = _CZ_TIMEZONE_OFFSET_PATTERN.match(normalized)
        if match:
            sign, hours = match.group(1), int(match.group(2))
            return f"{sign}{hours:02d}:00"
        if normalized in CZ_TIMEZONE_ABBREVIATION_OFFSETS:
            return CZ_TIMEZONE_ABBREVIATION_OFFSETS[normalized]
    return DEFAULT_CZ_TIMEZONE_OFFSET


def parse_damage(value: str | None) -> float | None:
    if not value or value.upper() in {"UNK", "UNKNOWN"}:
        return None
    normalized = value.strip().upper().replace(",", "")
    multiplier = 1
    if normalized.endswith("K"):
        multiplier = 1_000
        normalized = normalized[:-1]
    elif normalized.endswith("M"):
        multiplier = 1_000_000
        normalized = normalized[:-1]
    elif normalized.endswith("B"):
        multiplier = 1_000_000_000
        normalized = normalized[:-1]
    try:
        return float(normalized) * multiplier
    except ValueError:
        return None


def parse_timestamp(value: str | None, cz_timezone: str | None = None) -> str | None:
    """Parse NCEI's local BEGIN_DATE_TIME into an ISO string with a UTC offset.

    The returned string keeps NCEI's local wall-clock reading (the digits are
    not shifted) and appends the offset implied by cz_timezone, for example
    "1968-04-05T14:30:00-06:00". See parse_cz_timezone_offset for the offset
    lookup and its documented default.
    """
    if not value:
        return None
    for pattern in ("%d-%b-%y %H:%M:%S", "%d-%b-%y %H:%M:%S %Z", "%m/%d/%Y %H:%M:%S"):
        try:
            parsed = datetime.strptime(value.strip(), pattern)
            # Python maps two-digit 68 and 69 to 2068 and 2069. NCEI's historical
            # source contains those dates, while this project has no future events.
            if parsed.year > datetime.now().year:
                parsed = parsed.replace(year=parsed.year - 100)
            return f"{parsed.isoformat()}{parse_cz_timezone_offset(cz_timezone)}"
        except ValueError:
            continue
    return None


def value(row: dict[str, str], key: str) -> str | None:
    return row.get(key) or row.get(key.lower()) or None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--database", default=os.environ.get("DBT_DUCKDB_PATH", "weather.duckdb"))
    parser.add_argument("--append", action="store_true", help="Append records to an existing raw table instead of replacing it.")
    args = parser.parse_args()

    opener = gzip.open if args.input.suffix == ".gz" else open
    with opener(args.input, "rt", encoding="utf-8", errors="replace", newline="") as source:
        reader = csv.DictReader(source)
        rows = []
        for row in reader:
            state = STATE_NAME_TO_CODE.get((value(row, "STATE") or "").upper(), value(row, "STATE"))
            if value(row, "EVENT_TYPE") != "Tornado" or state not in COHORT_STATES:
                continue
            rows.append((
                value(row, "EVENT_ID"), value(row, "EVENT_TYPE"), state, value(row, "CZ_NAME"),
                parse_timestamp(value(row, "BEGIN_DATE_TIME"), value(row, "CZ_TIMEZONE")), value(row, "CZ_TIMEZONE"),
                value(row, "BEGIN_LOCATION"), value(row, "END_LOCATION"),
                value(row, "TOR_F_SCALE"), value(row, "TOR_LENGTH"), value(row, "TOR_WIDTH"), value(row, "BEGIN_LAT"),
                value(row, "BEGIN_LON"), value(row, "END_LAT"), value(row, "END_LON"), value(row, "INJURIES_DIRECT"),
                value(row, "DEATHS_DIRECT"), parse_damage(value(row, "DAMAGE_PROPERTY")), parse_damage(value(row, "DAMAGE_CROPS")),
                value(row, "EVENT_NARRATIVE"), "https://www.ncei.noaa.gov/stormevents/",
            ))

    con = duckdb.connect(args.database)
    con.execute("create schema if not exists raw")
    if not args.append:
        con.execute("drop table if exists raw.ncei_tornado_events")
    con.execute("""
      create table if not exists raw.ncei_tornado_events (
        event_id varchar, event_type varchar, state varchar, county varchar,
        occurred_at varchar, cz_timezone varchar,
        begin_location varchar, end_location varchar, tor_f_scale varchar, tor_length varchar,
        tor_width varchar, begin_lat varchar, begin_lon varchar, end_lat varchar, end_lon varchar,
        injuries_direct varchar, deaths_direct varchar, property_damage_usd double, crop_damage_usd double,
        event_narrative varchar, source_url varchar
      )
    """)
    if rows:
        con.executemany("insert into raw.ncei_tornado_events values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    con.close()
    print(f"Loaded {len(rows)} NCEI tornado events from {args.input}")


if __name__ == "__main__":
    main()
