# Nature Recovery Policy Explorer

## Overview

A policy scenario explorer for England that compares how different priorities
change the national pattern of nature recovery opportunity.

The project asks:

How do different policy priorities change which places appear strongest for nature recovery?

## Stack

- DuckDB
- dbt-duckdb
- Parquet / GeoParquet
- Python
- PMTiles
- MapLibre GL JS

## Current State

This repo currently includes:

- staged canonical hex base
- per-scenario scoring model
- cross-scenario comparison model
- publish exports for app use
- a working PMTiles layer
- a MapLibre app with scenario switching, filters, hover, and selection

## Main Outputs

Analytical tables:

- `hex_base`
- `scenario_scores`
- `scenario_comparison`
- `app_hexes`
- `scenario_summary`

Publish assets:

- `data/publish/app_hexes.parquet`
- `data/publish/app_hexes_tiles.fgb`
- `data/publish/policy_hexes.pmtiles`
- `data/publish/scenario_summary.parquet`
- `data/publish/scenario_summary.json`
- `data/publish/app_overview.json`
- `data/publish/app_hexes_points.json`
- `data/publish/tile_schema.json`

Application:

- `app/maplibre/`

## Rebuild Workflow

### 1. Run dbt models and seeds

```bash
cd /Users/laurencepengelly/rewilding-suitability/nature-recovery-policy-explorer
DBT_PROFILES_DIR=profiles .venv/bin/dbt seed --project-dir dbt
DBT_PROFILES_DIR=profiles .venv/bin/dbt run --project-dir dbt
DBT_PROFILES_DIR=profiles .venv/bin/dbt test --project-dir dbt
```

### 2. Export publish assets

```bash
.venv/bin/python scripts/export_publish_assets.py
```

This writes the app-facing files into `data/publish/`.

### 3. Build PMTiles

```bash
./scripts/build_pmtiles.sh
```

This builds:

- `data/publish/policy_hexes.pmtiles`

### 4. Serve locally

Use the byte-range server from the repo root:

```bash
cd /Users/laurencepengelly/rewilding-suitability
python3 scripts/serve_range_http.py --port 8003 --root /Users/laurencepengelly/rewilding-suitability
```

Then open:

- `http://localhost:8003/nature-recovery-policy-explorer/app/maplibre/`

## Key Files

Data and build:

- `dbt/models/staging/stg_hex_base.sql`
- `dbt/models/marts/fct_scenario_scores.sql`
- `dbt/models/marts/fct_scenario_comparison.sql`
- `dbt/models/exports/app_hexes.sql`
- `dbt/models/exports/scenario_summary.sql`
- `scripts/export_publish_assets.py`
- `scripts/build_pmtiles.sh`

Application:

- `app/maplibre/index.html`
- `app/maplibre/styles.css`
- `app/maplibre/main.js`

## What The App Does

- switches between five policy scenarios
- recolors the same national hex grid by scenario percentile
- filters stable-core and contested areas
- supports hover inspection
- supports click selection with sidebar detail

## Notes

- `policy_hexes_z9.pmtiles` is an earlier tileset kept during development
- `app_hexes_tiles_4326.fgb` is an intermediate reprojection artifact used during tile building
