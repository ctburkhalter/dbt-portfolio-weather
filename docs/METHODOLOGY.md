# Methodology and data contract

## Purpose

This project is a public analytics-engineering case study for the weather dashboard on chaseburkhalter.com. It turns public National Weather Service and NOAA NCEI data into a documented, tested, versioned interface for a portfolio application.

The subject is personal as well as technical. Tornadoes and severe weather are recurring realities in south Alabama, where the dashboard begins with Dothan's current alert status and then places Alabama history beside project-defined regional cohorts.

## Sources and refresh behavior

| Source | Purpose | Refresh | Important interpretation |
|---|---|---|---|
| National Weather Service alerts API | Current Tornado Watch and Tornado Warning status | Scheduled workflow, hourly | An alert is a forecast product, not a confirmed tornado event. |
| NOAA NCEI Storm Events bulk details files | Confirmed historical tornado events | Committed 1950-2024 baseline plus current-year source files, discovered dynamically and cached per UTC day | Damage survey records can be revised by NCEI releases. |
| Iowa State Mesonet Local Storm Reports | Preliminary tornado point reports after the latest confirmed NCEI event timestamp | Scheduled workflow, hourly | These reports are provisional, can include duplicates and corrections, and do not provide surveyed track geometry or final F/EF rating fields. |

The historical baseline is intentionally compact. `ingestion/build_historical_baseline.py` downloads the official NCEI files, retains only tornado records in the documented 13-state cohorts and source fields required by this project, and records exact filenames and retrieval time in `data/historical_baseline_metadata.json`.

## Modeling approach

```text
NWS API + NCEI bulk files + IEM Local Storm Reports
          |
          v
raw DuckDB tables
          |
          v
src normalization models
          |
          +--> dimensions: date, geography, tornado intensity
          |
          v
facts: active alerts, confirmed tornado events, preliminary point reports, current combined events
          |
          v
marts: seasonality, annual trends, county impact
          |
          v
versioned dashboard JSON + dbt docs
```

`src` models type and normalize source values without adding analytical interpretation. Dimensions define reusable calendar, cohort, and F or EF intensity definitions. Facts preserve the detailed event, report, and alert grains. `fct_tornado_events_current` keeps all confirmed NCEI records and appends preliminary IEM reports only after the latest confirmed NCEI timestamp. Marts supply compact chart aggregates. The export script retains event-level fields in a separate index so dashboard tooltips and detail panels do not need to infer information from aggregate charts.

## Cohorts

- Alabama: `AL`
- Dixie comparison cohort: `AL`, `AR`, `GA`, `LA`, `MS`, `TN`
- Tornado comparison cohort: `CO`, `IA`, `KS`, `NE`, `OK`, `SD`, `TX`

These are project-defined analytical cohorts, not official meteorological boundaries. They are used to give portfolio visitors a clear comparison frame without representing an authoritative definition of Dixie Alley or Tornado Alley.

## Safety and interpretation

- F and EF values classify observed damage. Published wind ranges are rating-based estimates and are never presented as direct wind measurements.
- The F and EF scales are retained explicitly. Severity rollups use `F2+/EF2+`, not a claim that the scales represent interchangeable measured winds.
- NCEI beginning and ending coordinates are endpoints. A dashboard line between them is an approximate endpoint connection, not a surveyed tornado path.
- Missing, malformed, or unrecognized ratings are normalized to the explicit `Unknown` dimension member. The original NCEI record remains the attribution source.
- Preliminary Local Storm Reports are point reports. They are labeled with `recordStatus = "preliminary"`, unavailable survey fields remain `null`, and they are not counted as F2/EF2+ or as confirmed tornado totals unless a future confirmed source provides a rating and event record.
- Current NWS products are displayed separately from historical confirmed events. The pipeline does not attribute an alert to a later tornado record.

## Published interfaces

The exporter creates versioned static contracts, all with `schemaVersion: "1.0"`:

- `data/portfolio-weather.v1.json`: live alert status, dashboard marts, event coverage metadata, and an `eventYearIndex` (`{year, count}` per year with data) used by the weather route. It intentionally carries no individual event records, so it stays small enough for the consumer's fetch cache to hold.
- `data/events/{year}.json`: one file per year of current events. Confirmed NCEI records include full detail (rating, wind estimate, path, endpoints, impacts, narrative, source). Preliminary IEM rows include point location, report text, `recordStatus`, `sourceSystem`, `sourceAttribution`, and `wfo`, with unavailable survey fields set to `null`. Nothing is trimmed; history is partitioned by year rather than shipped as a single array, and every year observed so far fits comfortably under a 2MB per-file budget.

The consumer website retrieves these through same-origin API routes. It validates the contract version, fetches only the year (or year range) a visitor selects, applies bounded event filters server-side, caches dashboard and event data for 15 minutes, and retains the most recent successful data during upstream failures.

## Quality controls

- Python regression tests cover NCEI date normalization, including the two-digit 1968/1969 boundary, invalid timestamps, damage parsing, and preliminary LSR timestamp parsing.
- dbt tests cover source event keys, allowed event and report types, unique and non-null dimension and fact keys, valid intensity scale values, record status values, null preliminary rating fields, confirmed-only annual tornado totals, and non-negative casualty measures where the source provides those measures.
- dbt source freshness measures NWS pipeline health through an ingestion-run record, including polls that legitimately return zero active tornado products.
- GitHub Actions runs ingestion tests, source freshness, dbt build, dbt docs generation, and JSON export before GitHub Pages deployment. A failing run ends before deployment, preserving the previous successful artifact.
