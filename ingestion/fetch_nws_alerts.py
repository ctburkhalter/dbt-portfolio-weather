"""Fetch current NWS tornado products into the raw DuckDB schema."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
import duckdb
import requests

BASE_URL = "https://api.weather.gov/alerts/active"
USER_AGENT = "chaseburkhalter.com south-alabama-tornado-watch (chase@chaseburkhalter.com)"


def fetch_alerts(params: dict[str, str]) -> list[dict]:
    response = requests.get(
        BASE_URL,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("features", [])


def parameter(properties: dict, name: str) -> str | None:
    value = properties.get("parameters", {}).get(name)
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value is not None else None


def rows_for_scope(scope: str, params: dict[str, str]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for feature in fetch_alerts(params):
        properties = feature.get("properties", {})
        rows.append({
            "alert_id": str(properties.get("id") or feature.get("id")),
            "scope": scope,
            "event": properties.get("event"),
            "headline": properties.get("headline"),
            "sent_at": properties.get("sent"),
            "effective_at": properties.get("effective"),
            "expires_at": properties.get("expires"),
            "severity": properties.get("severity"),
            "certainty": properties.get("certainty"),
            "urgency": properties.get("urgency"),
            "area_description": properties.get("areaDesc"),
            "detection": parameter(properties, "tornadoDetection"),
            "damage_threat": parameter(properties, "tornadoDamageThreat"),
            "motion_description": parameter(properties, "eventMotionDescription"),
            "source_url": properties.get("@id") or properties.get("id"),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=os.environ.get("DBT_DUCKDB_PATH", "weather.duckdb"))
    args = parser.parse_args()

    # The NWS API accepts comma-delimited values for the array-style event parameter.
    statewide = rows_for_scope("alabama", {"area": "AL", "event": "Tornado Warning,Tornado Watch"})
    dothan = rows_for_scope("dothan", {"point": "31.2232,-85.3905", "event": "Tornado Warning,Tornado Watch"})
    combined: dict[str, dict[str, str | None | bool]] = {}
    for row in statewide + dothan:
        alert_id = str(row["alert_id"])
        if alert_id not in combined:
            combined[alert_id] = {**row, "affects_dothan": row["scope"] == "dothan"}
        elif row["scope"] == "dothan":
            combined[alert_id]["affects_dothan"] = True
    rows = list(combined.values())

    con = duckdb.connect(args.database)
    con.execute("create schema if not exists raw")
    con.execute("drop table if exists raw.nws_ingestion_runs")
    con.execute("create table raw.nws_ingestion_runs (ingested_at timestamp, record_count integer)")
    con.execute("insert into raw.nws_ingestion_runs values (?, ?)", [datetime.now(timezone.utc).isoformat(), len(rows)])
    con.execute("drop table if exists raw.nws_active_alerts")
    con.execute("""
      create table raw.nws_active_alerts (
        alert_id varchar, scope varchar, affects_dothan boolean, event varchar, headline varchar, sent_at timestamp,
        effective_at timestamp, expires_at timestamp, severity varchar, certainty varchar,
        urgency varchar, area_description varchar, detection varchar, damage_threat varchar,
        motion_description varchar, source_url varchar, ingested_at timestamp
      )
    """)
    if rows:
        columns = list(rows[0])
        con.executemany(
            f"insert into raw.nws_active_alerts ({', '.join(columns)}) values ({', '.join(['?'] * len(columns))})",
            [tuple(row[column] for column in columns) for row in rows],
        )
    con.close()
    print(f"Loaded {len(rows)} active NWS tornado products")


if __name__ == "__main__":
    main()
