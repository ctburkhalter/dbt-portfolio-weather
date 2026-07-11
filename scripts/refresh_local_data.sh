#!/usr/bin/env bash
# Refreshes the local dbt DuckDB database with current data and rebuilds all
# models. Mirrors the ingestion sequence in .github/workflows/refresh.yml
# (historical baseline, newly discovered NCEI years, preliminary IEM reports)
# without the docs generation or GitHub Pages publish steps, which are not
# needed for local development.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${VIRTUAL_ENV:-}" && -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

export DBT_PROFILES_DIR=.
export DBT_DUCKDB_PATH="${DBT_DUCKDB_PATH:-weather.duckdb}"

recent_dir="$(mktemp -d)"
trap 'rm -rf "$recent_dir"' EXIT

echo "==> Loading historical NCEI baseline into $DBT_DUCKDB_PATH"
python ingestion/load_ncei_events.py --input data/StormEvents_details.csv.gz

echo "==> Discovering NCEI files for years after the baseline"
python ingestion/refresh_recent_ncei.py --output-dir "$recent_dir"

shopt -s nullglob
for file in "$recent_dir"/*.csv.gz; do
  echo "==> Appending $file"
  python ingestion/load_ncei_events.py --append --input "$file"
done

echo "==> Fetching preliminary IEM tornado reports"
python ingestion/fetch_preliminary_tornado_reports.py

echo "==> Running dbt build"
dbt build --target dev

echo "==> Done. $DBT_DUCKDB_PATH is up to date."
