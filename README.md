# South Alabama Tornado Watch Pipeline

This is the standalone companion data project for the portfolio `/weather` route. It uses Python ingestion, DuckDB, and dbt to publish a small dashboard contract, one JSON file per year of current tornado events, and dbt docs to GitHub Pages.

See [Methodology and data contract](docs/METHODOLOGY.md) for sources, lineage, cohorts, interpretation guardrails, published interfaces, and quality controls.

## Data semantics

- NWS records are current Tornado Watch and Tornado Warning products. They are not confirmed tornado events.
- NCEI Storm Events rows are historical confirmed events. The project retains rating, inferred wind-range, path length and width, endpoint coordinates, impacts, and narrative for event detail.
- Iowa State Mesonet Local Storm Reports are preliminary point reports. They are appended only after the latest confirmed NCEI event timestamp and remain labeled as preliminary.
- Endpoint coordinates are not a surveyed track. The dashboard describes any connecting line as an approximate endpoint connection.
- Dixie cohort: AL, AR, GA, LA, MS, TN. Tornado cohort: CO, IA, KS, NE, OK, SD, TX. These are documented project conventions, not official boundaries.

## Model layers and published contracts

| Layer | Models | Grain and responsibility |
|---|---|---|
| `src` | `src_nws__active_alerts`, `src_ncei__tornado_events`, `src_iem__preliminary_tornado_reports` | Typed source fields with no business interpretation beyond normalization. |
| `dim` | `dim_date`, `dim_geography`, `dim_tornado_intensity` | Reusable calendar, cohort, and F/EF rating definitions. Wind ranges remain explicitly damage-based estimates. |
| `fct` | `fct_active_tornado_alerts`, `fct_tornado_events`, `fct_preliminary_tornado_reports`, `fct_tornado_events_current` | One active alert product, one confirmed historical event, one preliminary point report, or the combined current event view. These facts are intentionally not joined as warning-to-tornado attribution. |
| `marts` | monthly seasonality, annual trend, county impact | Stable aggregates for the portfolio charts. Seasonality and county impact remain confirmed-only; annual trend uses the current combined event view but keeps `tornadoes` confirmed-only and exposes preliminary report counts separately. |

`scripts/publish_dashboard.py` exports:

- `portfolio-weather.v1.json`: dashboard metadata, live status, chart marts, event coverage metadata, and an `eventYearIndex` (`{year, count}` per year with data). No individual event records: this file stays small enough for the consumer's fetch cache to actually cache it.
- `events/{year}.json`: one file per year, each holding every current event for that year with source, status, rating, wind estimate, path, endpoints, impacts, and narrative where available. Confirmed NCEI rows are full event records. Preliminary IEM rows are point reports with unavailable survey fields set to `null` and available report attribution retained in `sourceAttribution` and `wfo`.

Nothing is trimmed or truncated: full history stays available, just partitioned by year instead of shipped as one array. The consumer fetches only the year (or years) a visitor actually asks for.

The interface is versioned because the portfolio page validates `schemaVersion = "1.0"` before treating a remote artifact as production data.

The event-map tab uses published beginning coordinates. For confirmed NCEI rows it can also render the published ending coordinate, but describes the connection only as an endpoint line because NCEI does not provide surveyed track geometry in this source. Preliminary IEM rows render as points only.

## Quality and operational behavior

- `raw.nws_ingestion_runs` records every successful NWS poll, including zero-alert results, so freshness measures pipeline health rather than the chance of an active warning.
- dbt validates source keys, accepted values, rating dimensions, non-negative injuries and fatalities, and fact uniqueness.
- The workflow runs source freshness, `dbt build`, JSON export, and dbt docs generation before publishing. A failure ends before deployment, preserving the last successful GitHub Pages artifact.
- The portfolio caches each published JSON file server-side for 15 minutes and falls back to a visibly labeled local fixture if no artifact URL is configured or the remote contract is invalid.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp profiles.yml.example profiles.yml
python ingestion/build_historical_baseline.py
python ingestion/load_ncei_events.py --input data/StormEvents_details.csv.gz
python ingestion/fetch_nws_alerts.py
python ingestion/fetch_preliminary_tornado_reports.py
DBT_PROFILES_DIR=. dbt build
DBT_PROFILES_DIR=. dbt docs generate
python scripts/publish_dashboard.py --output public/data
python -m unittest discover -s tests
```

Publish `public/` with GitHub Pages. Set the portfolio's `WEATHER_DATA_URL` to the resulting `data/portfolio-weather.v1.json` URL; the consumer derives each year shard's URL (`data/events/{year}.json`) from that same base path.

`ingestion/build_historical_baseline.py` is a deliberate one-time baseline refresh. It downloads NCEI details files for 1950 through 2024, retains only confirmed tornado events for the documented 13-state cohorts and fields required by the data contract, then records the exact source files and retrieval timestamp in `data/historical_baseline_metadata.json`. For constrained environments it can resume non-overlapping ranges with `--append`. Commit the resulting compact baseline and metadata to this public repository.

The scheduled workflow loads that committed historical baseline, discovers the latest official NCEI bulk files for every year after the baseline through the current year, and appends their cohort events before dbt builds. It then pulls preliminary IEM Local Storm Reports after the latest confirmed NCEI timestamp. Current-year NCEI bulk files are cached per UTC day so the hourly schedule only re-downloads and reprocesses them once a day, keeping the dashboard current without repeatedly downloading the full historical archive or hammering NCEI on every run. It fails before publishing if source freshness, dbt tests, or JSON export fail, leaving the previous GitHub Pages artifact intact.

## Deployment

1. Commit the source, baseline, and baseline metadata to the default branch of this public repository.
2. In repository settings, enable GitHub Pages with GitHub Actions as the deployment source.
3. Run the `Refresh tornado dashboard data` workflow once from the Actions tab.
4. Set the consumer website's `WEATHER_DATA_URL` environment variable to `https://<github-user>.github.io/dbt-portfolio-weather/data/portfolio-weather.v1.json`.

The pipeline contains no credentials. NWS requests include an identifiable user agent, while NCEI source files and IEM Local Storm Reports are public data. The portfolio caches the published contract server-side and retains its last valid response when the remote artifact is temporarily unavailable.
