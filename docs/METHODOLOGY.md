# Methodology and data contract

## Purpose

This project is a public analytics-engineering case study for the weather route on chaseburkhalter.com. It turns public NOAA NCEI data and Iowa State Mesonet preliminary reports into documented, tested, versioned interfaces for a tornado event explorer and dbt project explorer.

The subject is personal as well as technical. Tornadoes and severe weather are recurring realities in south Alabama, making the source distinctions, event grain, and preliminary-versus-confirmed boundary a useful analytics-engineering case study.

## Sources and refresh behavior

| Source | Purpose | Refresh | Important interpretation |
|---|---|---|---|
| NOAA NCEI Storm Events bulk details files | Confirmed historical tornado events | Committed 1950-2024 baseline plus current-year source files, discovered dynamically and cached per UTC day | Damage survey records can be revised by NCEI releases. Timestamps are local to the event (see Timestamp offsets). |
| Iowa State Mesonet Local Storm Reports | Preliminary tornado point reports after the latest confirmed NCEI event timestamp | Scheduled workflow, daily | These reports are provisional, can include duplicates and corrections, and do not provide surveyed track geometry or final F/EF rating fields. Timestamps are UTC. |

The historical baseline is intentionally compact. `ingestion/build_historical_baseline.py` downloads the official NCEI files, retains only tornado records in the documented 13-state cohorts and source fields required by this project, and records exact filenames and retrieval time in `data/historical_baseline_metadata.json`.

## Modeling approach

```text
NCEI bulk files + IEM Local Storm Reports
          |
          v
raw DuckDB tables
          |
          v
source-system staging views
          |
          +--> dimensions: geography, tornado intensity
          |
          v
facts: confirmed tornado events, preliminary point reports, current combined events
          |
          v
marts: seasonality, annual trends, county impact
          |
          v
versioned event JSON + dbt project explorer + dbt docs
```

Staging views normalize one source relation each. Ephemeral intermediate models apply cohort membership and conform the source shapes. The contracted `fct_tornado_events` mart keeps confirmed NCEI events and appends preliminary IEM reports only after the latest confirmed UTC instant. A deterministic seed governs F and EF intensity definitions.

## Cohorts

- Alabama: `AL`
- Dixie comparison cohort: `AL`, `AR`, `GA`, `LA`, `MS`, `TN`
- Tornado comparison cohort: `CO`, `IA`, `KS`, `NE`, `OK`, `SD`, `TX`

These are project-defined analytical cohorts, not official meteorological boundaries. `macros/cohort_flags.sql` derives the three membership flags in one place for both intermediate source-conformance branches.

## Timestamp offsets

Every published `occurredAt` value carries an explicit UTC offset suffix; the pipeline never publishes a naive timestamp string. A naive string is ambiguous about which clock it was recorded on, and `new Date(naiveString)` in a browser parses it in the *viewer's* local timezone before display, so the same event would render at a different time for different visitors.

- **Confirmed NCEI rows** keep NCEI's local wall-clock reading (the digits are not shifted) and append the offset implied by the source's `CZ_TIMEZONE` field, for example `2020-01-01T14:30:00-06:00` for a Central time event. `ingestion/load_ncei_events.py::parse_cz_timezone_offset` recognizes both the modern explicit-offset NCEI form (`CST-6`) and the older bare-abbreviation form used in early Storm Events years (`CST`, with no digit), and defaults to `-06:00` (CST, the modal timezone across this project's cohort states) for any value it doesn't recognize.
- **Preliminary IEM rows** are ingested in UTC and always carry a `+00:00` suffix.

Internally, `stg_ncei__tornado_events` and `stg_iem__preliminary_tornado_reports` expose `occurred_at_utc`, a UTC-equivalent instant used for the canonical fact cutoff, and `occurred_at_utc_offset`, the offset reattached at publish time. Year-shard bucketing is based on the event-local year from `occurred_at`, so a late-December local event never moves to the wrong shard.

## Safety and interpretation

- F and EF values classify observed damage. Published wind ranges are rating-based estimates and are never presented as direct wind measurements.
- The F and EF scales are retained explicitly. Severity rollups use `F2+/EF2+`, not a claim that the scales represent interchangeable measured winds.
- NCEI beginning and ending coordinates are endpoints. An event-detail line between them is an approximate endpoint connection, not a surveyed tornado path.
- Missing, malformed, or unrecognized ratings are normalized to the explicit `Unknown` dimension member. The original NCEI record remains the attribution source.
- Preliminary Local Storm Reports are point reports. They are labeled with `recordStatus = "preliminary"`, unavailable survey fields remain `null`, and they are not counted as F2/EF2+ or as confirmed tornado totals unless a future confirmed source provides a rating and event record.

## Published interfaces

The exporter creates contracts under `data/v2/` with `schemaVersion: "2.0"`. The contract uses `eventKey` while retaining source-native `eventId`:

- `data/v2/portfolio-weather.json`: event coverage metadata and an `eventYearIndex` (`{year, count}` per year with data) used by the weather route. It intentionally carries no individual event records, so it stays small enough for the consumer's fetch cache to hold.
- `data/v2/events/{year}.json`: one file per year of current events. Confirmed NCEI records include full detail (rating, wind estimate, path, endpoints, impacts, narrative, source). Preliminary IEM rows include point location, report text, `recordStatus`, `sourceSystem`, `sourceAttribution`, and `wfo`, with unavailable survey fields set to `null`. Nothing is trimmed; history is partitioned by year rather than shipped as a single array. Every `occurredAt` in these files carries an explicit UTC offset (see Timestamp offsets above), and the publisher enforces a 2MB per-file budget, raising rather than silently publishing an oversized shard.
- `data/v2/dbt-project.json`: a compact projection of the successful run's dbt manifest, catalog, and saved build run results. The workflow preserves `target/build_run_results.json` before dbt docs generation replaces the active run-results file. The artifact exposes the public project file tree, source text, model and source descriptions, direct lineage, test outcomes, relation names, build summary, and commit-pinned source links for the portfolio's native project explorer.

The consumer website retrieves these through same-origin API routes. It validates the contract version, fetches only the year (or year range) a visitor selects, applies bounded event filters server-side, caches event and project-explorer data for 15 minutes, and retains the most recent successful data during upstream failures. The project explorer never calls the GitHub API from a visitor's browser.

## Quality controls

- Python regression tests cover NCEI date normalization (including the two-digit 1968/1969 boundary and invalid timestamps), the CZ_TIMEZONE offset parser (modern and historical NCEI forms, and the documented default), damage parsing (including the `B` billions suffix), preliminary LSR timestamp parsing, and current-year NCEI file discovery (the January window where a new year has no published file yet).
- dbt tests cover source event keys, allowed event and report types, unique and non-null dimension and fact keys, non-null event timestamps, valid intensity scale values, record status values, null preliminary rating fields, confirmed-only annual tornado totals, and non-negative casualty measures where the source provides those measures.
- GitHub Actions runs ingestion tests, dbt build, dbt docs generation, event export, and project-explorer export before GitHub Pages deployment. A failing run ends before deployment, preserving the previous successful artifact.
