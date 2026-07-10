"""Export dbt marts to the JSON contracts consumed by the portfolio site."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

MONTHS = [(1, "Jan"), (2, "Feb"), (3, "Mar"), (4, "Apr"), (5, "May"), (6, "Jun"), (7, "Jul"), (8, "Aug"), (9, "Sep"), (10, "Oct"), (11, "Nov"), (12, "Dec")]


def records(con: duckdb.DuckDBPyConnection, query: str) -> list[dict]:
    cursor = con.execute(query)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def iso(value: object) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=os.environ.get("DBT_DUCKDB_PATH", "weather.duckdb"))
    parser.add_argument("--output", default="dist")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(args.database, read_only=True)
    monthly_rows = records(con, "select * from marts.mart_monthly_seasonality")
    monthly_index = {(row["region"], row["month_number"]): row for row in monthly_rows}
    monthly = {
        region: [
            {
                "month": month,
                "tornadoes": int(monthly_index.get((region, month_number), {}).get("tornadoes", 0)),
                "significantTornadoes": int(monthly_index.get((region, month_number), {}).get("significant_tornadoes", 0)),
            }
            for month_number, month in MONTHS
        ]
        for region in ("alabama", "dixie", "tornado")
    }
    annual = [
        {
            "year": row["year"],
            "tornadoes": row["tornadoes"],
            "significantTornadoes": row["significant_tornadoes"],
            "confirmedTornadoes": row["confirmed_tornadoes"],
            "preliminaryTornadoReports": row["preliminary_tornado_reports"],
        }
        for row in records(con, "select * from marts.mart_annual_trend_current order by year")
    ]
    county = [
        {"county": row["county"], "tornadoes": row["tornadoes"], "significantTornadoes": row["significant_tornadoes"], "injuries": row["injuries"], "maxRating": row["max_rating"] or "Unknown"}
        for row in records(con, "select * from marts.mart_county_impact limit 10")
    ]
    alert_rows = records(con, """
      select alert_id, max(event) as event, max(headline) as headline, max(sent_at) as sent_at,
        max(expires_at) as expires_at, max(severity) as severity, max(certainty) as certainty,
        max(urgency) as urgency, max(area_description) as area_description, max(detection) as detection,
        max(damage_threat) as damage_threat, max(motion_description) as motion_description,
        max(source_url) as source_url, bool_or(affects_dothan) as affects_dothan
      from fct.fct_active_tornado_alerts
      group by 1
    """)
    alerts = [{
        "id": row["alert_id"], "event": row["event"], "headline": row["headline"] or row["event"],
        "sentAt": iso(row["sent_at"]), "expiresAt": iso(row["expires_at"]), "severity": row["severity"],
        "certainty": row["certainty"], "urgency": row["urgency"], "areaDescription": row["area_description"],
        "detection": row["detection"], "damageThreat": row["damage_threat"], "motionDescription": row["motion_description"],
        "sourceUrl": row["source_url"],
    } for row in alert_rows]

    coverage = records(con, """
      select
        max(occurred_at) filter (where record_status = 'confirmed') as confirmed_through,
        min(occurred_at) filter (where record_status = 'preliminary') as preliminary_from,
        max(occurred_at) filter (where record_status = 'preliminary') as preliminary_through,
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
        occurred_at = iso(row["occurred_at"])
        events_by_year[row["occurred_at"].year].append({
            "eventId": row["event_id"], "regionIds": regions, "occurredAt": occurred_at, "state": row["state"],
            "county": row["county"], "beginLocation": row["begin_location"], "endLocation": row["end_location"],
            "ratingCode": row["rating_code"] or "Unknown", "scaleSystem": row["scale_system"], "ratingValue": row["rating_value"],
            "windEstimateLowMph": row["wind_estimate_low_mph"], "windEstimateHighMph": row["wind_estimate_high_mph"],
            "windEstimateNote": row["wind_estimate_note"], "pathLengthMiles": row["path_length_miles"], "pathWidthYards": row["path_width_yards"],
            "beginLatitude": row["begin_latitude"], "beginLongitude": row["begin_longitude"], "endLatitude": row["end_latitude"], "endLongitude": row["end_longitude"],
            "injuries": row["injuries"], "fatalities": row["fatalities"], "propertyDamageUsd": row["property_damage_usd"],
            "cropDamageUsd": row["crop_damage_usd"], "narrative": row["narrative"], "sourceUrl": row["source_url"],
            "recordStatus": row["record_status"], "sourceSystem": row["source_system"], "isSurveyedTrack": row["is_surveyed_track"],
        })

    events_dir = output / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    event_year_index = []
    for year in sorted(events_by_year, reverse=True):
        year_events = events_by_year[year]
        (events_dir / f"{year}.json").write_text(
            json.dumps({"schemaVersion": "1.0", "year": year, "events": year_events}, default=str, separators=(",", ":")),
            encoding="utf-8",
        )
        event_year_index.append({"year": year, "count": len(year_events)})

    payload = {
        "schemaVersion": "1.0",
        "sourceMode": "pipeline",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCoverage": "NWS current tornado products, filtered NOAA NCEI confirmed Storm Events records, and preliminary Iowa State Mesonet Local Storm Reports after the latest NCEI cutoff for the documented project cohorts.",
        "eventCoverage": {
            "confirmedThrough": iso(coverage["confirmed_through"]),
            "preliminaryFrom": iso(coverage["preliminary_from"]),
            "preliminaryThrough": iso(coverage["preliminary_through"]),
            "preliminaryCount": coverage["preliminary_count"],
        },
        "liveStatus": {"dothanHasActiveAlert": any(row["affects_dothan"] for row in alert_rows), "alabamaHasActiveAlert": bool(alert_rows), "alerts": alerts},
        "monthlySeasonality": monthly,
        "annualTrend": annual,
        "countyImpact": county,
        "eventYearIndex": event_year_index,
    }
    (output / "portfolio-weather.v1.json").write_text(json.dumps(payload, default=str, separators=(",", ":")), encoding="utf-8")
    con.close()
    total_events = sum(len(v) for v in events_by_year.values())
    print(f"Published {total_events} event records across {len(events_by_year)} year shards and {len(alerts)} active alert records")


if __name__ == "__main__":
    main()
