# Historical source extract

`StormEvents_details.csv.gz` is the compact, filtered NCEI baseline artifact. Its intended committed coverage is 1950 through 2024. Check `historical_baseline_metadata.json` for its exact current year coverage before treating it as ready for publication. It contains only `EVENT_TYPE = Tornado` records from the documented 13-state project cohorts and only the source columns required to build this project's published contract. The full national NCEI archive is never committed or published.

Build or refresh it deliberately:

```bash
python ingestion/build_historical_baseline.py
```

The generated `historical_baseline_metadata.json` records the exact NCEI files, source index, retrieval timestamp, year coverage, filter, and event counts. Commit both files together.

`demo_storm_events.csv` is a synthetic integration fixture. It supports local dbt and contract validation only and is never presented as NCEI history by the portfolio dashboard.
