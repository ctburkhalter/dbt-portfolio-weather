"""Export the current tornado event fact table to the JSON contracts consumed by the portfolio site."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

# Next.js's fetch cache skips any response body over 2MB; this is that same
# budget, documented in README.md and METHODOLOGY.md, enforced here so a
# regression fails loudly instead of silently producing an uncacheable shard.
MAX_SHARD_BYTES = 2 * 1024 * 1024


def records(con: duckdb.DuckDBPyConnection, query: str) -> list[dict]:
    cursor = con.execute(query)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def iso(value: object) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def iso_with_offset(value: object, offset: str | None) -> str | None:
    formatted = iso(value)
    if formatted is None or not offset:
        return formatted
    return f"{formatted}{offset}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=os.environ.get("DBT_DUCKDB_PATH", "weather.duckdb"))
    parser.add_argument("--output", default="dist")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(args.database, read_only=True)
    coverage = records(con, """
      select
        arg_max(occurred_at, occurred_at_utc) filter (where record_status = 'confirmed') as confirmed_through,
        arg_max(occurred_at_utc_offset, occurred_at_utc) filter (where record_status = 'confirmed') as confirmed_through_offset,
        arg_min(occurred_at, occurred_at_utc) filter (where record_status = 'preliminary') as preliminary_from,
        arg_min(occurred_at_utc_offset, occurred_at_utc) filter (where record_status = 'preliminary') as preliminary_from_offset,
        arg_max(occurred_at, occurred_at_utc) filter (where record_status = 'preliminary') as preliminary_through,
        arg_max(occurred_at_utc_offset, occurred_at_utc) filter (where record_status = 'preliminary') as preliminary_through_offset,
        count(*) filter (where record_status = 'preliminary') as preliminary_count
      from fct.fct_tornado_events_current
    """)[0]

    event_rows = records(con, "select * from fct.fct_tornado_events_current order by occurred_at desc")
    events_by_year: dict[int, list[dict]] = defaultdict(list)
    for row in event_rows:
        regions = []
        if row["is_alabama"]: regions.append("alabama")
        if row["is_dixie_cohort"]: regions.append("dixie")
        if row["is_tornado_cohort"]: regions.append("tornado")
        occurred_at = iso_with_offset(row["occurred_at"], row["occurred_at_utc_offset"])
        events_by_year[row["occurred_at"].year].append({
            "eventId": row["event_id"], "regionIds": regions, "occurredAt": occurred_at, "state": row["state"],
            "county": row["county"], "beginLocation": row["begin_location"], "endLocation": row["end_location"],
            "ratingCode": row["rating_code"], "scaleSystem": row["scale_system"], "ratingValue": row["rating_value"],
            "windEstimateLowMph": row["wind_estimate_low_mph"], "windEstimateHighMph": row["wind_estimate_high_mph"],
            "windEstimateNote": row["wind_estimate_note"], "pathLengthMiles": row["path_length_miles"], "pathWidthYards": row["path_width_yards"],
            "beginLatitude": row["begin_latitude"], "beginLongitude": row["begin_longitude"], "endLatitude": row["end_latitude"], "endLongitude": row["end_longitude"],
            "injuries": row["injuries"], "fatalities": row["fatalities"], "propertyDamageUsd": row["property_damage_usd"],
            "cropDamageUsd": row["crop_damage_usd"], "narrative": row["narrative"], "sourceUrl": row["source_url"],
            "sourceAttribution": row["source_attribution"], "wfo": row["wfo"],
            "recordStatus": row["record_status"], "sourceSystem": row["source_system"], "isSurveyedTrack": row["is_surveyed_track"],
        })

    events_dir = output / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    event_year_index = []
    for year in sorted(events_by_year, reverse=True):
        year_events = events_by_year[year]
        shard_path = events_dir / f"{year}.json"
        shard_bytes = json.dumps({"schemaVersion": "1.0", "year": year, "events": year_events}, default=str, separators=(",", ":")).encode("utf-8")
        if len(shard_bytes) > MAX_SHARD_BYTES:
            raise ValueError(
                f"events/{year}.json is {len(shard_bytes)} bytes, over the documented {MAX_SHARD_BYTES}-byte budget "
                "(README.md and METHODOLOGY.md); Next.js's fetch cache skips responses over 2MB."
            )
        shard_path.write_bytes(shard_bytes)
        event_year_index.append({"year": year, "count": len(year_events)})

    payload = {
        "schemaVersion": "1.0",
        "sourceMode": "pipeline",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCoverage": "Filtered NOAA NCEI confirmed Storm Events records and preliminary Iowa State Mesonet Local Storm Reports after the latest NCEI cutoff for the documented project cohorts.",
        "eventCoverage": {
            "confirmedThrough": iso_with_offset(coverage["confirmed_through"], coverage["confirmed_through_offset"]),
            "preliminaryFrom": iso_with_offset(coverage["preliminary_from"], coverage["preliminary_from_offset"]),
            "preliminaryThrough": iso_with_offset(coverage["preliminary_through"], coverage["preliminary_through_offset"]),
            "preliminaryCount": coverage["preliminary_count"],
        },
        "eventYearIndex": event_year_index,
    }
    (output / "portfolio-weather.v1.json").write_text(json.dumps(payload, default=str, separators=(",", ":")), encoding="utf-8")
    con.close()
    total_events = sum(len(v) for v in events_by_year.values())
    print(f"Published {total_events} event records across {len(events_by_year)} year shards")


if __name__ == "__main__":
    main()
