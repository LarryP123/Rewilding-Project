# Rewilding Suitability

A spatial decision-support project for identifying high-impact rewilding opportunities in England by balancing biodiversity recovery, habitat connectivity, flood mitigation, carbon opportunity, and agricultural tradeoffs.

## Project status

This repository is currently set up for an MVP focused on England and a 1 km hex grid. The immediate goal is to build a reproducible geospatial pipeline that:

- ingests raw environmental layers,
- standardises them into a common CRS and storage format,
- aggregates features to a shared analysis grid,
- produces scenario-based suitability scores,
- prepares outputs for notebooks, reports, and an interactive map app.

## MVP scope

The first version prioritises layers that are practical to integrate and defensible as decision-support signals:

- land cover context,
- existing priority habitat,
- agricultural land quality,
- flood opportunity,
- England boundary and optional LNRS summaries.

Biodiversity occurrence data and peat restoration features can be added once the baseline workflow is stable.

## Repository structure

```text
data/
  raw/                Raw source files
  interim/            Standardised and subsetted data products
notebooks/            Exploration and analysis notebooks
outouts/              Methods and supporting project notes
src/                  Reusable pipeline code
```

## Planned pipeline

1. Ingest raw layers and record source metadata.
2. Reproject all geometry to British National Grid (`EPSG:27700`).
3. Build a 1 km hex grid for England.
4. Derive per-hex feature tables for habitat, agriculture, flood, and future biodiversity or peat layers.
5. Score each hex under multiple scenarios.
6. Export map-ready outputs.

## Getting started

Create an environment and install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Example workflow in Python:

```python
from pathlib import Path

import geopandas as gpd

from src.build_grid import build_hex_grid
from src.features import add_habitat_share_feature, add_alc_opportunity_feature
from src.score import apply_scenarios

england = gpd.read_file(Path("data/raw/boundaries/england_boundary.gpkg")).to_crs(27700)
grid = build_hex_grid(england, cell_diameter_m=1000)
```

Current MVP runner:

```python
from pathlib import Path

from src.pipeline import build_mvp_outputs

build_mvp_outputs(out_dir=Path("data/interim/mvp"), cell_diameter_m=20000)
```

Production-style run with the official England boundary:

```bash
python scripts/run_official_boundary_mvp.py --cell-diameter-m 1000
```

The runner now caches the cleaned ALC layer at `data/interim/alc_clean.parquet`
and reuses existing boundary, CORINE, habitat, grid, and score outputs inside
the chosen `--out-dir` when present. Use `--no-reuse-existing` if you want to
force a rebuild.

Export top-ranked candidate hexes from a scored layer:

```bash
python scripts/export_top_candidates.py \
  --scores-path data/interim/mvp_official_boundary/hex_scores.parquet \
  --scenario scenario_balanced \
  --top-n 100
```

Right now the pipeline uses:

- the local `data/interim/corine_subset.parquet` layer for habitat-context features,
- a proxy analysis boundary derived from available ALC coverage when no official England boundary is supplied.

## Outputs

The main intended outputs are:

- a scored geospatial layer for England hexes,
- scenario tables for ranking candidate areas,
- methods and assumptions documentation,
- notebooks for validation and case studies,
- a future interactive map application.

## Notes

The `outouts/` directory name is preserved to match the current repo layout. If you want, that can be renamed to `outputs/` in a later cleanup pass.
