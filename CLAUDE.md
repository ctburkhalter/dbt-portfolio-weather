# CLAUDE.md

Read and follow [AGENTS.md](AGENTS.md). It is the authoritative operating guide for this standalone dbt and weather-data pipeline.

Before changing a model, ingestion script, published JSON field, or GitHub Actions workflow:

1. Preserve the distinction between active NWS alerts and confirmed NCEI events.
2. Preserve the event-contract semantics for F/EF ratings, inferred wind ranges, and endpoint coordinates.
3. Update the relevant source or model documentation and the README in the same change.
4. Run source freshness, `dbt build`, JSON export, and dbt docs generation when data is available.

The consumer website is maintained in the sibling `chaseburkhalter.com` repository. Update its weather API types, tracking plan, analytics-system documentation, and on-page implementation notes whenever this project's versioned contract changes.
