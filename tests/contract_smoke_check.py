"""Assert the published JSON contract's shape and size budget.

This is invoked explicitly by .github/workflows/ci.yml after that workflow
builds the demo fixture (data/demo_storm_events.csv) through dbt and
scripts/publish_dashboard.py. It is deliberately named so that
`python -m unittest discover -s tests` (unittest's default "test*.py"
discovery pattern) does not pick it up: this check runs `dbt build` and
writes real files, which does not belong in the fast unit-test suite that
.github/workflows/refresh.yml also runs before every scheduled ingestion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MAX_SHARD_BYTES = 2 * 1024 * 1024
REQUIRED_INDEX_KEYS = {"schemaVersion", "sourceMode", "generatedAt", "sourceCoverage", "eventCoverage", "eventYearIndex"}
_UTC_OFFSET_SUFFIX = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


def check(output_dir: Path) -> list[str]:
    failures: list[str] = []

    index_path = output_dir / "portfolio-weather.v1.json"
    if not index_path.exists():
        return [f"{index_path} does not exist"]
    index = json.loads(index_path.read_text(encoding="utf-8"))

    if index.get("schemaVersion") != "1.0":
        failures.append(f"portfolio-weather.v1.json schemaVersion is {index.get('schemaVersion')!r}, expected '1.0'")

    missing_keys = REQUIRED_INDEX_KEYS - index.keys()
    if missing_keys:
        failures.append(f"portfolio-weather.v1.json is missing required top-level keys: {sorted(missing_keys)}")

    year_index = index.get("eventYearIndex", [])
    total_events = sum(entry.get("count", 0) for entry in year_index)
    if total_events == 0:
        failures.append("eventYearIndex reports zero total events; the demo fixture should have produced at least one")

    events_dir = output_dir / "events"
    shard_paths = sorted(events_dir.glob("*.json")) if events_dir.exists() else []
    if not shard_paths:
        failures.append(f"no shard files found under {events_dir}")

    for shard_path in shard_paths:
        shard_bytes = shard_path.stat().st_size
        if shard_bytes > MAX_SHARD_BYTES:
            failures.append(f"{shard_path} is {shard_bytes} bytes, over the documented {MAX_SHARD_BYTES}-byte budget")
        shard = json.loads(shard_path.read_text(encoding="utf-8"))
        if shard.get("schemaVersion") != "1.0":
            failures.append(f"{shard_path} schemaVersion is {shard.get('schemaVersion')!r}, expected '1.0'")
        for event in shard.get("events", []):
            occurred_at = event.get("occurredAt")
            if not occurred_at or not _UTC_OFFSET_SUFFIX.search(occurred_at):
                failures.append(f"{shard_path} event {event.get('eventId')!r} occurredAt {occurred_at!r} has no UTC offset suffix")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="public/data", help="Directory holding the published portfolio-weather.v1.json and events/ shards.")
    args = parser.parse_args()

    failures = check(Path(args.output))
    if failures:
        print("Contract smoke check failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    print("Contract smoke check passed: schemaVersion, required keys, event coverage, and shard size budget all hold.")


if __name__ == "__main__":
    main()
