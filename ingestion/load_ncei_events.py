"""Load a filtered NCEI Storm Events CSV or CSV.GZ into DuckDB."""

from __future__ import annotations

import argparse
import csv
import gzip
import os
from datetime import datetime
from pathlib import Path

import duckdb

COHORT_STATES = {"AL", "AR", "GA", "LA", "MS", "TN", "CO", "IA", "KS", "NE", "OK", "SD", "TX"}
STATE_NAME_TO_CODE = {
    "ALABAMA": "AL", "ARKANSAS": "AR", "GEORGIA": "GA", "LOUISIANA": "LA", "MISSISSIPPI": "MS", "TENNESSEE": "TN",
    "COLORADO": "CO", "IOWA": "IA", "KANSAS": "KS", "NEBRASKA": "NE", "OKLAHOMA": "OK", "SOUTH DAKOTA": "SD", "TEXAS": "TX",
}


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
    try:
        return float(normalized) * multiplier
    except ValueError:
        return None


def parse_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    for pattern in ("%d-%b-%y %H:%M:%S", "%d-%b-%y %H:%M:%S %Z", "%m/%d/%Y %H:%M:%S"):
        try:
            parsed = datetime.strptime(value.strip(), pattern)
            # Python maps two-digit 68 and 69 to 2068 and 2069. NCEI's historical
            # source contains those dates, while this project has no future events.
            if parsed.year > datetime.now().year:
                parsed = parsed.replace(year=parsed.year - 100)
            return parsed.isoformat()
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
                parse_timestamp(value(row, "BEGIN_DATE_TIME")), value(row, "BEGIN_LOCATION"), value(row, "END_LOCATION"),
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
        event_id varchar, event_type varchar, state varchar, county varchar, occurred_at timestamp,
        begin_location varchar, end_location varchar, tor_f_scale varchar, tor_length varchar,
        tor_width varchar, begin_lat varchar, begin_lon varchar, end_lat varchar, end_lon varchar,
        injuries_direct varchar, deaths_direct varchar, property_damage_usd double, crop_damage_usd double,
        event_narrative varchar, source_url varchar
      )
    """)
    if rows:
        con.executemany("insert into raw.ncei_tornado_events values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    con.close()
    print(f"Loaded {len(rows)} NCEI tornado events from {args.input}")


if __name__ == "__main__":
    main()
