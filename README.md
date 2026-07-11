# South Alabama Tornado Watch Pipeline

This is the standalone companion data project for the portfolio `/weather` route. It uses Python ingestion, DuckDB, and dbt to publish a compact event-discovery contract, one JSON file per year of current tornado events, a versioned dbt project explorer contract, and dbt docs to GitHub Pages.

See [Methodology and data contract](docs/METHODOLOGY.md) for sources, lineage, cohorts, interpretation guardrails, published interfaces, and quality controls.

## Data Semantics

- NCEI Storm Events rows are historical confirmed events. The project retains rating, inferred wind-range, path length and width, endpoint coordinates, impacts, and narrative for event detail.
- Iowa State Mesonet Local Storm Reports are preliminary point reports. They are appended only after the latest confirmed NCEI event timestamp and remain labeled as preliminary.
- Endpoint coordinates are not a surveyed track. The event explorer describes any connecting line as an approximate endpoint connection.
- Dixie cohort: AL, AR, GA, LA, MS, TN. Tornado cohort: CO, IA, KS, NE, OK, SD, TX. These are documented project conventions, not official boundaries.
- Published event timestamps always carry an explicit UTC offset (for example `-06:00` or `+00:00`), never a naive local time. See "Timestamp offsets" below.

## Model layers and published contracts

| Layer | Models | Grain and responsibility |
|---|---|---|
| `src` | `src_ncei__tornado_events`, `src_iem__preliminary_tornado_reports` | Typed source fields with no business interpretation beyond normalization. |
| `dim` | `dim_geography`, `dim_tornado_intensity` | Reusable cohort and F/EF rating definitions. Wind ranges remain explicitly damage-based estimates. |
| `fct` | `fct_tornado_events`, `fct_preliminary_tornado_reports`, `fct_tornado_events_current` | One confirmed historical event, one preliminary point report, or the combined current event view. |
| `marts` | monthly seasonality, annual trend, county impact | Documented aggregate models retained for lineage and testing in the dbt project explorer. They are not rendered as portfolio charts. |

`scripts/publish_dashboard.py` exports:

- `portfolio-weather.v1.json`: event coverage metadata and an `eventYearIndex` (`{year, count}` per year with data). No individual event records: this file stays small enough for the consumer's fetch cache to actually cache it.
- `events/{year}.json`: one file per year, each holding every current event for that year with source, status, rating, wind estimate, path, endpoints, impacts, and narrative where available. Confirmed NCEI rows are full event records. Preliminary IEM rows are point reports with unavailable survey fields set to `null` and available report attribution retained in `sourceAttribution` and `wfo`. Each shard is enforced to stay under a 2MB budget at publish time; the publisher raises if a shard exceeds it.

Nothing is trimmed or truncated: full history stays available, just partitioned by year instead of shipped as one array. The consumer fetches only the year (or years) a visitor actually asks for.

The interface is versioned because the portfolio page validates `schemaVersion = "1.0"` before treating a remote artifact as production data.

`scripts/publish_project_explorer.py` exports `dbt-project.v1.json` after `dbt build` and `dbt docs generate`. It is a compact static projection of the exact manifest, catalog, and saved build run results from that successful run. The workflow copies `target/run_results.json` to `target/build_run_results.json` before docs generation, because dbt docs replaces the current run-results file. The artifact includes model and source metadata, direct lineage, attached test outcomes, a curated public project file tree with source text, and GitHub links pinned to the commit that produced it. The portfolio derives this artifact and the dbt docs URL from `WEATHER_DATA_URL`, so it never reads repository code directly from a visitor's browser.

The event-detail map uses published beginning coordinates. For confirmed NCEI rows it can also render the published ending coordinate, but describes the connection only as an endpoint line because NCEI does not provide surveyed track geometry in this source. Preliminary IEM rows render as points only.

### Timestamp offsets

Every published `occurredAt` value is an ISO-8601 string with an explicit UTC offset suffix, never a naive local time:

- Confirmed NCEI rows keep NCEI's local wall-clock reading and append the offset implied by the source's `CZ_TIMEZONE` field (for example `2020-01-01T14:30:00-06:00` for a Central time event). `ingestion/load_ncei_events.py::parse_cz_timezone_offset` parses both the modern explicit-offset NCEI form (`CST-6`) and the older bare-abbreviation form used in early Storm Events years (`CST`), defaulting to `-06:00` (CST, the modal timezone across this project's cohort states) for anything unrecognized.
- Preliminary IEM rows are ingested in UTC and always carry a `+00:00` suffix.

This matters because a naive timestamp string gets parsed in the *browser's* local timezone before display, so the same event would render at different times for different visitors. See `docs/METHODOLOGY.md` for the full contract statement.

## Quality and operational behavior

- dbt validates source keys, accepted values, rating dimensions, non-negative injuries and fatalities, non-null event timestamps, and fact uniqueness.
- The workflow runs ingestion tests, `dbt build`, JSON export, and dbt docs generation before publishing. A failure ends before deployment, preserving the last successful GitHub Pages artifact.
- The portfolio caches each published JSON file server-side for 15 minutes and falls back to a visibly labeled local fixture if no artifact URL is configured or the remote contract is invalid.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ingestion/build_historical_baseline.py
python ingestion/load_ncei_events.py --input data/StormEvents_details.csv.gz
python ingestion/fetch_preliminary_tornado_reports.py
DBT_PROFILES_DIR=. dbt build
cp target/run_results.json target/build_run_results.json
DBT_PROFILES_DIR=. dbt docs generate
python scripts/publish_dashboard.py --output public/data
python scripts/publish_project_explorer.py --output public/data/dbt-project.v1.json
python -m unittest discover -s tests
```

`profiles.yml` is tracked directly (it contains no secrets, just a DuckDB path read from the `DBT_DUCKDB_PATH` environment variable), so no copy step is needed before running dbt.

Publish `public/` with GitHub Pages. Set the portfolio's `WEATHER_DATA_URL` to the resulting `data/portfolio-weather.v1.json` URL; the consumer derives each year shard's URL (`data/events/{year}.json`) from that same base path.

`ingestion/build_historical_baseline.py` is a deliberate one-time baseline refresh. It downloads NCEI details files for 1950 through 2024, retains only confirmed tornado events for the documented 13-state cohorts and fields required by the data contract, then records the exact source files and retrieval timestamp in `data/historical_baseline_metadata.json`. For constrained environments it can resume non-overlapping ranges with `--append`. Commit the resulting compact baseline and metadata to this public repository.

The scheduled workflow runs once daily. It loads that committed historical baseline, discovers the latest official NCEI bulk files for every year after the baseline through the current year, and appends their cohort events before dbt builds. It then pulls preliminary IEM Local Storm Reports after the latest confirmed NCEI timestamp. Current-year NCEI bulk files are cached per UTC day so reruns do not repeatedly download the same source files. The run fails before publishing if ingestion tests, dbt tests, or JSON export fail, leaving the previous GitHub Pages artifact intact. Year discovery tolerates a missing current-year NCEI file (NCEI typically doesn't publish a new year's file until days to weeks in) but still hard-fails if a past expected year is missing.

## Deployment

1. Commit the source, baseline, and baseline metadata to the default branch of this public repository.
2. In repository settings, enable GitHub Pages with GitHub Actions as the deployment source.
3. Run the `Refresh tornado event explorer data` workflow once from the Actions tab.
4. Set the consumer website's `WEATHER_DATA_URL` environment variable to `https://<github-user>.github.io/dbt-portfolio-weather/data/portfolio-weather.v1.json`.

The pipeline contains no credentials. NCEI source files and IEM Local Storm Reports are public data. The portfolio caches the published contract server-side and retains its last valid response when the remote artifact is temporarily unavailable.
