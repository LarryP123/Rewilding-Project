# Rewilding Suitability

A national screening and prioritisation workflow for rewilding in England.
It combines a defined set of geospatial signals into comparable 1 km opportunity scores, shortlist tables, candidate-zone summaries, and a map app.
It is designed to narrow England down to plausible areas for further review, not to make site-level recommendations or predict ecological outcomes.

## Project status

This repository is currently set up for an MVP focused on England and a 1 km hex grid.
The immediate goal is to build a reproducible geospatial pipeline that:

- ingests raw environmental layers,
- standardises them into a common CRS and storage format,
- aggregates features to a shared analysis grid,
- produces scenario-based suitability scores,
- prepares outputs for notebooks, reports, and an interactive map app.

## MVP scope

The first version prioritises layers that are practical to integrate and defensible as decision-support signals:

- land cover context,
- existing priority habitat,
- observation-based bird and mammal layers built from verified NBN/iRecord records,
- agricultural land quality,
- flood opportunity from a dedicated Environment Agency style flood layer,
- England boundary for the analysis extent plus optional LNRS geography for policy slicing and summaries.

The biodiversity dimension now combines bird and mammal observation indicators rather than relying on birds alone.
It is still a pragmatic screening proxy rather than a full biodiversity model, and it remains sensitive to recording effort.
The canonical published run requires dedicated flood and peat source datasets.
CORINE is retained only as an explicit local-development fallback so the pipeline can still run before those raw layers are added locally.

## What This Project Is

This project is a national spatial screening workflow for England.
Its job is to turn a defined set of land-focused inputs into comparable 1 km cell scores under a small number of policy-style scenario lenses.
Those scores are then packaged into shortlist exports, cluster summaries, validation notes, and an interactive explorer so the outputs can be reviewed and challenged.

## What It Does

The canonical published workflow in this repository:

- builds or reuses a national 1 km hex grid for England,
- derives habitat, biodiversity-observation, agricultural, flood, and peat-related features per cell,
- scores each cell under `scenario_nature_first`, `scenario_balanced`, and `scenario_low_conflict`,
- exports shortlist and candidate-zone outputs from the same scored layer,
- and packages those outputs into documentation and a standalone HTML explorer.

## What It Does Not Claim

This project does not claim to:

- identify final rewilding sites,
- predict ecological outcomes or delivery feasibility,
- replace local ecological assessment, ownership review, or policy due diligence,
- or serve as a causal model of biodiversity recovery, carbon outcomes, or flood performance.

High-ranking cells should be treated as candidate areas for follow-up, not as recommendations in themselves.

## Repository structure

```text
data/
  raw/                Raw source files
  interim/            Standardised and subsetted data products
notebooks/            Exploration and analysis notebooks
outputs/              Methods and supporting project notes
src/                  Reusable pipeline code
```

## Planned pipeline

1. Ingest raw layers and record source metadata.
2. Reproject all geometry to British National Grid (`EPSG:27700`).
3. Build a 1 km hex grid for England.
4. Derive per-hex feature tables for habitat, biodiversity, agriculture, flood, and peat.
5. Score each hex under multiple scenarios.
6. Export map-ready outputs.

## Getting started

Create an environment and install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
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

Canonical published run with the official England boundary and dedicated flood/peat inputs:

```bash
python scripts/run_official_boundary_mvp.py --cell-diameter-m 1000
```

End-to-end canonical publication pass from one scored run:

```bash
python scripts/publish_canonical_run.py --verbose
```

If the raw dedicated flood and peat layers are very large, prepare simplified
scoring-ready versions first:

```bash
python scripts/prepare_canonical_sources.py
```

With dedicated flood and peat layers supplied explicitly:

```bash
python scripts/run_official_boundary_mvp.py \
  --cell-diameter-m 1000 \
  --flood-path data/raw/flood/ea_flood_zones.gpkg \
  --peat-path data/raw/peat/england_peat_map.gdb \
  --peat-layer peaty_soil_extent_v1
```

The runner now caches the cleaned ALC layer at `data/interim/alc_clean.parquet`
and reuses existing boundary, CORINE, habitat, grid, and score outputs inside
the chosen `--out-dir` when present. Use `--no-reuse-existing` if you want to
force a rebuild.

Export top-ranked candidate hexes from the canonical scored layer:

```bash
python scripts/export_top_candidates.py \
  --scores-path data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet \
  --scenario scenario_balanced \
  --top-n 100
```

Add LNRS names and policy-area summaries when an LNRS boundary layer is available:

```bash
python scripts/export_top_candidates.py \
  --scores-path data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet \
  --scenario scenario_balanced \
  --top-n 100 \
  --lnrs-path data/raw/reference/lnrs_boundaries.geojson
```

Generate clustered candidate zones with LNRS slicing carried through to the zone summary:

```bash
python scripts/summarize_candidate_clusters.py \
  --scores-path data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet \
  --scenario scenario_balanced \
  --top-n 100 \
  --lnrs-path data/raw/reference/lnrs_boundaries.geojson
```

Right now the local-development workflow can use:

- the local `data/interim/corine_subset.parquet` layer for habitat-context features,
- cached observation-based bird and mammal layers downloaded from NBN Atlas verified iRecord records for England,
- dedicated flood and peat layers under `data/raw/flood/` and `data/raw/peat/`, with explicit CORINE fallback proxies reserved for non-canonical local runs,
- and a proxy analysis boundary derived from available ALC coverage when no official England boundary is supplied.

The current biodiversity workflow is intentionally controlled in scope:

- birds remain the original observation taxon,
- mammals are the single Phase 2 addition,
- each taxon is aggregated to the 1 km hex grid as species richness plus record count,
- each taxon score is damped by a simple record-coverage term before entering scenario scoring,
- and the scenario layer uses a combined `biodiversity_observation_score_raw` so biodiversity is no longer bird-only.

This does not remove observation bias. It only makes that bias more explicit and a little less fragile:

- richness without enough records is down-weighted,
- absence of records is treated as low confidence rather than ecological absence,
- and hotspots may still partly reflect where active recorders spend time.

The current canonical published result is the dedicated-data 1 km stack rooted
at `data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet`. Local reruns
that use proxy fallback can coexist for development and smoke testing, but they
should not be treated as published outputs.
The corresponding release checkpoint is written to
`outputs/release/canonical_v5.json`, with `outputs/release/latest.json` updated
to the same payload after a successful canonical publish pass.

## Outputs

The main intended outputs are:

- a scored geospatial layer for England hexes,
- scenario tables for ranking candidate areas under different policy lenses,
- LNRS-sliced shortlist and candidate-zone summaries when LNRS geography is supplied,
- methods and assumptions documentation,
- notebooks for validation and case studies,
- a standalone interactive map application.

Build the packaged shortlist explorer:

```bash
python scripts/build_map_app.py \
  --scores-path data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet
```

This writes a self-contained HTML app to
`outputs/app/rewilding_opportunity_explorer.html`. The app packages the union
of the top-ranked cells from each scenario, supports scenario switching and
interactive filtering, and includes a per-cell explanation panel that exposes
the weighted score components.

## Interpretation

The most useful reading of this repository is:
"given this set of inputs and assumptions, which parts of England repeatedly look promising enough to justify closer review?"

That is a much narrower claim than "where rewilding should happen."
The outputs are intended to support screening, discussion, and challenge, not to close the decision.

## Validation and regression checks

The repo now includes a small hardening layer for local and CI validation:

- `pytest` exercises spatial overlay / nearest-join behavior and score-range guards.
- `python -m src.data_manifest` validates that the key raw and interim datasets tracked in `data/manifest.toml` are present.

Run both locally with:

```bash
pytest
python -m src.data_manifest
```

## Notes

Generated project outputs live in `outputs/`.
