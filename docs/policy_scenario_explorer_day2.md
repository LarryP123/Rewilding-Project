# Nature Recovery Policy Explorer

## Day 2 Build Files

This document covers the next setup step after the Day 1 scaffold:

- folder scaffold
- `.gitignore`
- first staging model
- setup commands

The goal for Day 2 is to get the first base table into `DuckDB` and make it queryable through `dbt`.

## Folder Scaffold

Create this structure inside the new repo:

```text
nature-recovery-policy-explorer/
  README.md
  .gitignore
  pyproject.toml
  data/
    raw/
    processed/
    publish/
  dbt/
    dbt_project.yml
    analyses/
    macros/
    models/
      staging/
      marts/
      exports/
    seeds/
    tests/
  scripts/
  docs/
```

## `.gitignore`

Use this as the starting `.gitignore`:

```gitignore
# Python
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/

# dbt
dbt/target/
dbt/dbt_packages/
logs/

# data artifacts
data/raw/*
!data/raw/.gitkeep
data/processed/*
!data/processed/.gitkeep
data/publish/*
!data/publish/.gitkeep

# local OS noise
.DS_Store
Thumbs.db

# editors
.vscode/
.idea/
```

Add empty marker files:

```text
data/raw/.gitkeep
data/processed/.gitkeep
data/publish/.gitkeep
```

## Base Dataset Assumption

For Day 2, assume the new project reuses the canonical processed hex layer from the existing atlas project.

Example input:

```text
data/raw/hex_base_source.parquet
```

At this stage, the simplest approach is:

1. manually copy or symlink the existing canonical hex dataset into the new repo
2. standardize its schema in a dbt staging model

The Day 2 objective is not to rebuild feature engineering yet.

## `stg_hex_base.sql`

Create:

`dbt/models/staging/stg_hex_base.sql`

```sql
with source as (
    select *
    from read_parquet('../data/raw/hex_base_source.parquet')
),

renamed as (
    select
        cast(hex_id as varchar) as hex_id,
        admin_name,
        geometry,
        cast(restoration_opportunity_score as double) as restoration_opportunity_score,
        cast(flood_opportunity_score_raw as double) as flood_opportunity_score_raw,
        cast(peat_opportunity_score_raw as double) as peat_opportunity_score_raw,
        cast(agri_opportunity_score_raw as double) as agri_opportunity_score_raw,
        cast(habitat_mosaic_score as double) as habitat_mosaic_score,
        cast(biodiversity_observation_score_raw as double) as biodiversity_observation_score_raw,
        cast(connectivity_score as double) as connectivity_score,
        cast(priority_habitat_share as double) as priority_habitat_share,
        cast(distance_to_priority_habitat_m as double) as distance_to_priority_habitat_m,
        cast(cell_area_ratio as double) as cell_area_ratio,
        cast(undersized_cell_penalty as double) as undersized_cell_penalty
    from source
)

select *
from renamed
```

This does three things:

- fixes the column contract
- makes types explicit
- gives the rest of the project one clean base model to depend on

## Optional Schema Test

Create:

`dbt/models/staging/stg_hex_base.yml`

```yaml
version: 2

models:
  - name: stg_hex_base
    columns:
      - name: hex_id
        tests:
          - not_null
          - unique
      - name: restoration_opportunity_score
        tests:
          - not_null
      - name: flood_opportunity_score_raw
        tests:
          - not_null
      - name: peat_opportunity_score_raw
        tests:
          - not_null
      - name: agri_opportunity_score_raw
        tests:
          - not_null
      - name: habitat_mosaic_score
        tests:
          - not_null
      - name: biodiversity_observation_score_raw
        tests:
          - not_null
```

## Day 2 Setup Commands

Run these after creating the scaffold:

```bash
mkdir -p data/raw data/processed data/publish
mkdir -p dbt/analyses dbt/macros dbt/models/staging dbt/models/marts dbt/models/exports dbt/seeds dbt/tests
touch data/raw/.gitkeep data/processed/.gitkeep data/publish/.gitkeep
```

If using a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then run:

```bash
dbt debug --project-dir dbt
dbt seed --project-dir dbt
dbt run --project-dir dbt --select stg_hex_base
dbt test --project-dir dbt --select stg_hex_base
```

## Expected Day 2 Outcome

By the end of Day 2, you want:

- the repo scaffold in place
- the base hex parquet copied into `data/raw/`
- `scenario_weights` seeded into DuckDB
- `stg_hex_base` materialized successfully
- base schema tests passing

That gives the project a clean base table for the next step:

- scenario scoring
- ranking
- comparison outputs

## Next File After Day 2

The next build file should be:

`dbt/models/marts/fct_scenario_scores.sql`

That is where the seeded scenario weights start driving the scoring logic.
