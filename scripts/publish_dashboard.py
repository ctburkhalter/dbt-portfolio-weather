"""Publish versioned weather contracts from the canonical dbt event fact."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

MAX_SHARD_BYTES = 2 * 1024 * 1024
MODEL_ID = "model.south_alabama_tornado_watch.fct_tornado_events"
EVENT_COLUMNS = (
    "event_key", "event_id", "occurred_at", "occurred_at_utc", "occurred_at_utc_offset",
    "state", "county", "begin_location", "end_location", "rating_code", "scale_system",
    "rating_value", "intensity_class", "wind_estimate_low_mph", "wind_estimate_high_mph",
    "wind_estimate_note", "path_length_miles", "path_width_yards", "begin_latitude",
    "begin_longitude", "end_latitude", "end_longitude", "injuries", "fatalities",
    "property_damage_usd", "crop_damage_usd", "narrative", "source_url", "is_alabama",
    "is_dixie_cohort", "is_tornado_cohort", "source_attribution", "wfo", "record_status",
    "source_system", "is_surveyed_track",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_relation(manifest_path: Path, run_results_path: Path | None) -> str:
    manifest = read_json(manifest_path)
    node = manifest.get("nodes", {}).get(MODEL_ID)
    if not node or not node.get("relation_name") or not node.get("config", {}).get("enabled", True):
        raise ValueError(f"{MODEL_ID} is missing, disabled, or has no relation in {manifest_path}")
    if run_results_path and run_results_path.exists():
        results = {item.get("unique_id"): item.get("status") for item in read_json(run_results_path).get("results", [])}
        if results.get(MODEL_ID) not in {"success", "pass"}:
            raise ValueError(f"{MODEL_ID} was not successful in {run_results_path}")
    return node["relation_name"]


def records(connection: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, Any]]:
    cursor = connection.execute(query)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def iso(value: object) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def iso_with_offset(value: object, offset: str | None) -> str | None:
    formatted = iso(value)
    return f"{formatted}{offset}" if formatted is not None and offset else formatted


def event_payload(row: dict[str, Any]) -> dict[str, Any]:
    regions = [name for name, flag in (("alabama", "is_alabama"), ("dixie", "is_dixie_cohort"), ("tornado", "is_tornado_cohort")) if row[flag]]
    payload = {
        "eventKey": row["event_key"], "eventId": row["event_id"], "regionIds": regions,
        "occurredAt": iso_with_offset(row["occurred_at"], row["occurred_at_utc_offset"]),
        "state": row["state"], "county": row["county"], "beginLocation": row["begin_location"],
        "endLocation": row["end_location"], "ratingCode": row["rating_code"],
        "scaleSystem": row["scale_system"], "ratingValue": row["rating_value"],
        "windEstimateLowMph": row["wind_estimate_low_mph"], "windEstimateHighMph": row["wind_estimate_high_mph"],
        "windEstimateNote": row["wind_estimate_note"], "pathLengthMiles": row["path_length_miles"],
        "pathWidthYards": row["path_width_yards"], "beginLatitude": row["begin_latitude"],
        "beginLongitude": row["begin_longitude"], "endLatitude": row["end_latitude"],
        "endLongitude": row["end_longitude"], "injuries": row["injuries"],
        "fatalities": row["fatalities"], "propertyDamageUsd": row["property_damage_usd"],
        "cropDamageUsd": row["crop_damage_usd"], "narrative": row["narrative"],
        "sourceUrl": row["source_url"], "sourceAttribution": row["source_attribution"],
        "wfo": row["wfo"], "recordStatus": row["record_status"],
        "sourceSystem": row["source_system"], "isSurveyedTrack": row["is_surveyed_track"],
    }
    validate_event(payload)
    return payload


def validate_event(event: dict[str, Any]) -> None:
    required = {"eventKey", "eventId", "occurredAt", "state", "regionIds", "recordStatus", "sourceSystem", "isSurveyedTrack"}
    missing = required - event.keys()
    if missing or not event["eventId"] or not event["eventKey"]:
        raise ValueError(f"Invalid event contract; missing or empty fields: {sorted(missing)}")
    valid_pair = (event["recordStatus"], event["sourceSystem"]) in {("confirmed", "ncei_storm_events"), ("preliminary", "iem_lsr")}
    if not valid_pair or event["isSurveyedTrack"] is not False:
        raise ValueError(f"Invalid source semantics for {event.get('eventKey', event['eventId'])}")


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def publish(database: str, output: Path, manifest: Path, run_results: Path | None) -> None:
    relation = canonical_relation(manifest, run_results)
    with duckdb.connect(database, read_only=True) as connection:
        rows = records(connection, f"select {', '.join(EVENT_COLUMNS)} from {relation} order by occurred_at_utc desc, event_key")
    events_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        events_by_year[row["occurred_at"].year].append(event_payload(row))

    schema_version = "2.0"
    events_dir = output / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    expected_files = {f"{year}.json" for year in events_by_year}
    for stale in events_dir.glob("*.json"):
        if stale.name not in expected_files: stale.unlink()
    index = []
    for year in sorted(events_by_year, reverse=True):
        content = json.dumps({"schemaVersion": schema_version, "year": year, "events": events_by_year[year]}, separators=(",", ":")).encode()
        if len(content) > MAX_SHARD_BYTES: raise ValueError(f"events/{year}.json exceeds {MAX_SHARD_BYTES} bytes")
        atomic_write(events_dir / f"{year}.json", content)
        index.append({"year": year, "count": len(events_by_year[year])})

    confirmed = [row for row in rows if row["record_status"] == "confirmed"]
    preliminary = [row for row in rows if row["record_status"] == "preliminary"]
    latest_confirmed = max(confirmed, key=lambda row: row["occurred_at_utc"]) if confirmed else None
    earliest_preliminary = min(preliminary, key=lambda row: row["occurred_at_utc"]) if preliminary else None
    latest_preliminary = max(preliminary, key=lambda row: row["occurred_at_utc"]) if preliminary else None
    coverage_value = lambda row: iso_with_offset(row["occurred_at"], row["occurred_at_utc_offset"]) if row else None
    payload = {
        "schemaVersion": schema_version, "sourceMode": "pipeline",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCoverage": "Filtered NOAA NCEI confirmed Storm Events records and preliminary Iowa State Mesonet Local Storm Reports after the latest NCEI cutoff for the documented project cohorts.",
        "eventCoverage": {"confirmedThrough": coverage_value(latest_confirmed), "preliminaryFrom": coverage_value(earliest_preliminary), "preliminaryThrough": coverage_value(latest_preliminary), "preliminaryCount": len(preliminary)},
        "eventYearIndex": index,
    }
    if sum(item["count"] for item in index) != len(rows): raise ValueError("Event year index does not reconcile")
    atomic_write(output / "portfolio-weather.json", json.dumps(payload, separators=(",", ":")).encode())
    print(f"Published v2 with {len(rows)} events across {len(index)} year shards")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=os.environ.get("DBT_DUCKDB_PATH", "weather.duckdb"))
    parser.add_argument("--output", default="public/data/v2")
    parser.add_argument("--manifest", default="target/manifest.json")
    parser.add_argument("--run-results", default="target/build_run_results.json")
    args = parser.parse_args()
    publish(args.database, Path(args.output), Path(args.manifest), Path(args.run_results))


if __name__ == "__main__": main()
