# Historical source extract

`StormEvents_details.csv.gz` is the compact, filtered NCEI baseline artifact. Its intended committed coverage is 1950 through 2024. Check `historical_baseline_metadata.json` for its exact current year coverage before treating it as ready for publication. It contains only `EVENT_TYPE = Tornado` records from the documented 13-state project cohorts and only the source columns required to build this project's published contract. The full national NCEI archive is never committed or published.

Build or refresh it deliberately:

```bash
python ingestion/build_historical_baseline.py
```

The generated `historical_baseline_metadata.json` records the exact NCEI files, source index, retrieval timestamp, year coverage, filter, and event counts. Commit both files together.

**Current baseline provenance:** source is the NOAA NCEI Storm Events bulk details files (`https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/`), retrieved 2026-07-10, covering 1950 through 2024 (46,246 filtered tornado events across the documented 13-state cohorts). See `historical_baseline_metadata.json` for the exact per-year source filenames and event counts behind this total.

`demo_storm_events.csv` is a synthetic integration fixture. It supports local dbt and contract validation only and is never presented as NCEI history by the portfolio dashboard.
