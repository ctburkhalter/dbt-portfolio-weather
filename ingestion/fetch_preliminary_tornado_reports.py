"""Load preliminary tornado Local Storm Reports from Iowa State Mesonet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
from datetime import datetime, timedelta, timezone

import duckdb
import requests

from load_ncei_events import COHORT_STATES

IEM_LSR_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/lsr.py"
SOURCE_URL = "https://mesonet.agron.iastate.edu/request/gis/lsrs.phtml"
USER_AGENT = "dbt-portfolio-weather/1.0 (public portfolio weather pipeline)"
CHUNK_DAYS = 31


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse an IEM LSR timestamp into a timezone-aware UTC datetime.

    IEM reports are already in UTC (a bare "YYYYMMDDHHMM" or space-separated
    value with no zone marker is IEM's own UTC wall clock, not a local time).
    The return value always carries tzinfo=UTC so isoformat() emits an
    explicit "+00:00" suffix instead of a naive string.
    """
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    if normalized.endswith("+00"):
        normalized = f"{normalized}:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for pattern in ("%Y%m%d%H%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(normalized, pattern)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def value(row: dict[str, str], key: str) -> str | None:
    return row.get(key) or row.get(key.lower()) or row.get(key.upper()) or None


def report_id(row: dict[str, str]) -> str:
    # REMARK is part of the identity hash, so an IEM correction to a report's
    # remark text (not uncommon for preliminary LSRs) changes this eventId
    # between runs. That is a known instability, accepted for now: dropping
    # REMARK would reduce churn but raises collision risk between distinct
    # reports that otherwise share timestamp, location, and office, and
    # that tradeoff needs validation against real duplicate-report patterns
    # before changing.
    identity = "|".join(
        (value(row, key) or "").strip()
        for key in ("VALID", "WFO", "TYPETEXT", "CITY", "COUNTY", "STATE", "LAT", "LON", "REMARK")
    )
    return f"iem_lsr_{hashlib.sha1(identity.encode('utf-8')).hexdigest()[:16]}"


def parse_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_rows(start: datetime, end: datetime) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
        response = requests.get(
            IEM_LSR_URL,
            params={
                "sts": cursor.isoformat().replace("+00:00", "Z"),
                "ets": chunk_end.isoformat().replace("+00:00", "Z"),
                "type": "TORNADO",
                "state": ",".join(sorted(COHORT_STATES)),
                "fmt": "csv",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        rows.extend(row for row in reader if (value(row, "TYPETEXT") or "").upper() == "TORNADO")
        cursor = chunk_end
    return rows


def latest_confirmed_timestamp(con: duckdb.DuckDBPyConnection) -> datetime | None:
    # raw.ncei_tornado_events.occurred_at is a varchar holding a full ISO-8601
    # string with an explicit UTC offset (see load_ncei_events.parse_timestamp).
    # Casting the whole string to TIMESTAMP normalizes through the embedded
    # offset to a UTC-equivalent naive value, which is what DuckDB's cast does
    # deterministically regardless of session timezone, so max() here compares
    # events in true chronological order even though individual rows carry
    # different local offsets (CST/EST/MST).
    try:
        value = con.execute("select max(cast(occurred_at as timestamp)) from raw.ncei_tornado_events").fetchone()[0]
    except duckdb.CatalogException:
        return None
    return value.replace(tzinfo=timezone.utc) if isinstance(value, datetime) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=os.environ.get("DBT_DUCKDB_PATH", "weather.duckdb"))
    parser.add_argument("--start", help="UTC ISO timestamp. Defaults to latest confirmed NCEI event.")
    parser.add_argument("--end", help="UTC ISO timestamp. Defaults to now.")
    args = parser.parse_args()

    con = duckdb.connect(args.database)
    cutoff = parse_timestamp(args.start) if args.start else latest_confirmed_timestamp(con)
    start = cutoff + timedelta(seconds=1) if cutoff else datetime(datetime.now(timezone.utc).year, 1, 1, tzinfo=timezone.utc)
    end = parse_timestamp(args.end) if args.end else datetime.now(timezone.utc)

    con.execute("create schema if not exists raw")
    con.execute("drop table if exists raw.preliminary_tornado_reports")
    con.execute("""
      create table raw.preliminary_tornado_reports (
        report_id varchar,
        valid_at varchar,
        report_type varchar,
        state varchar,
        county varchar,
        city varchar,
        source varchar,
        remark varchar,
        latitude double,
        longitude double,
        wfo varchar,
        magnitude varchar,
        magnitude_qualifier varchar,
        source_url varchar,
        fetched_at timestamp
      )
    """)

    if end <= start:
        con.close()
        print("Loaded 0 preliminary tornado reports because the selected range is empty")
        return

    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rows_by_id = {}
    for row in fetch_rows(start, end):
        valid_at = parse_timestamp(value(row, "VALID"))
        if valid_at is None:
            continue
        row_id = report_id(row)
        rows_by_id[row_id] = (
            row_id,
            valid_at.isoformat(),
            (value(row, "TYPETEXT") or "").upper(),
            (value(row, "STATE") or "").upper(),
            value(row, "COUNTY"),
            value(row, "CITY"),
            value(row, "SOURCE"),
            value(row, "REMARK"),
            parse_float(value(row, "LAT")),
            parse_float(value(row, "LON")),
            value(row, "WFO"),
            value(row, "MAG"),
            value(row, "QUALIFIER") or value(row, "QUALIFY"),
            SOURCE_URL,
            fetched_at,
        )

    rows = list(rows_by_id.values())
    if rows:
        con.executemany("insert into raw.preliminary_tornado_reports values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    con.close()
    print(f"Loaded {len(rows)} preliminary tornado reports from IEM LSRs between {start.isoformat()} and {end.isoformat()}")


if __name__ == "__main__":
    main()
