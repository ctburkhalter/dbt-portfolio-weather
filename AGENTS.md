# AGENTS.md

This repository is the standalone data-pipeline companion to the `/weather` route on [chaseburkhalter.com](https://chaseburkhalter.com). It is public by design and publishes static artifacts for the portfolio site.

## Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ingestion/load_ncei_events.py --input data/StormEvents_details.csv.gz
python ingestion/fetch_nws_alerts.py
python ingestion/fetch_preliminary_tornado_reports.py
DBT_PROFILES_DIR=. dbt source freshness
DBT_PROFILES_DIR=. dbt build
DBT_PROFILES_DIR=. dbt docs generate
python scripts/publish_dashboard.py --output public/data
python -m unittest discover -s tests
```

Use `DBT_DUCKDB_PATH=/tmp/south-alabama-tornado.duckdb` for disposable local validation. Do not commit `weather.duckdb`, `target/`, `logs/`, `public/`, virtual environments, or Python cache files.

## Architecture and contracts

- Python ingests NCEI historical confirmed tornado events, current NWS Tornado Watch and Tornado Warning products, and preliminary Iowa State Mesonet Local Storm Reports into DuckDB.
- dbt models source data through `src`, `dim`, `fct`, and `marts` layers. Preserve that lineage in model changes.
- `scripts/publish_dashboard.py` creates the versioned `portfolio-weather.v1.json` contract (dashboard metadata, live status, marts, event coverage, `eventYearIndex`) and one `events/{year}.json` file per year of current events, consumed by the portfolio's same-origin weather API. No individual events are embedded in `portfolio-weather.v1.json`; keep it that way so it stays cacheable.
- GitHub Actions refreshes recent NCEI files, validates source freshness and dbt tests, then publishes JSON and dbt docs through GitHub Pages. A failed run must leave the previous published artifact available.

## Data semantics and guardrails

- NWS alerts are active forecast products, not confirmed tornadoes. Do not join alerts to historical events as causal attribution.
- Preliminary IEM Local Storm Reports are point reports, not final confirmed NCEI events. Keep `record_status` and `source_system` visible when combining them with confirmed events.
- NCEI F and EF ratings are damage-based classifications. Wind ranges must be labeled estimates, never measured wind speeds.
- Begin and end coordinates are event endpoints. If rendered as a connection, label it an approximate endpoint connection, not a surveyed tornado track.
- Dixie and Tornado Alley cohorts are project-defined comparison groups, not official boundaries.
- Retain source attribution and event narrative in the published event contract where available.

## Documentation contract

Documentation changes are part of feature changes. Keep `README.md`, this file, `CLAUDE.md`, model/source documentation, the GitHub workflow, and the portfolio site's weather documentation synchronized when changing a data model, published field, refresh process, or data claim. Record the baseline's source and retrieval date in `data/README.md`.

## Writing and quality

- Do not use em dashes.
- Prefer specific, source-backed claims over marketing language.
- Add or update dbt tests for data-quality rules and run `dbt build` before handoff.
- Do not place production artifact URLs or access credentials in source code. The website receives the artifact URL through its `WEATHER_DATA_URL` environment variable.
