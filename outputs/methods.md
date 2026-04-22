# Methods Note

## Purpose

This project is a national screening and prioritisation workflow for rewilding in England.
It combines a defined set of geospatial signals into comparable 1 km cell scores so England can be narrowed to plausible areas for closer review.
This is a screening tool, not a causal model, not a site-selection engine, and not a site-level recommendation.

## What This Run Does

The canonical run turns habitat, observation-based biodiversity, agricultural, flood, and peat-related signals into three scenario views over the same national hex grid.
Those scenario scores are then used to produce shortlist tables, candidate-zone summaries, validation outputs, and a standalone explorer.

## What This Run Does Not Claim

This run does not claim to identify final rewilding sites, predict ecological outcomes, model delivery feasibility, or replace local ecological and practical review.

## Canonical Run

- Canonical release name: `canonical_v5`
- Canonical scored layer: `data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet`
- Cells scored: 204,703
- Study area: England using the official England analysis boundary in British National Grid (`EPSG:27700`)
- Analysis unit: 1 km hexagonal grid cells
- Run profile recorded in the score layer: `canonical_published`
- Release checkpoint: not generated in this run

## Core Inputs In This Run

- Habitat context from the locally prepared habitat proxy used in the MVP workflow
- Published flood source contract: `data/raw/flood/ea_flood_zones.gpkg`
- Published peat source contract: `data/raw/peat/england_peat_map.gdb`
- Flood opportunity source recorded in the score layer: `dedicated_dataset`
- Flood source path recorded in the score layer: `data/interim/canonical_sources/ea_flood_zones_simplified.parquet`
- Flood clean artifact recorded in the score layer: `data/interim/flood_ea_flood_zones_simplified_clean.parquet`
- Peat opportunity source recorded in the score layer: `dedicated_dataset`
- Peat source path recorded in the score layer: `data/interim/canonical_sources/england_peat_map_simplified.parquet`
- Peat clean artifact recorded in the score layer: `data/interim/peat_england_peat_map_simplified_clean.parquet`
- Agricultural opportunity from Agricultural Land Classification
- Biodiversity opportunity from combined bird and mammal observation indicators carried in this score layer
- Mammal observation coverage was included as the controlled Phase 2 biodiversity expansion
- Run metadata sidecar: `data/interim/mvp_official_boundary_1km_v5/run_metadata.json`

## Canonical Contract

- Required dedicated flood and peat inputs: `True`
- Fallback policy: Development runs may fall back to CORINE proxies, but the canonical published run may not.

## Scoring Logic

Each input is transformed onto a common 0 to 100 interpretation so that higher values mean stronger apparent restoration opportunity.
The repo currently carries three scenario views:

- `scenario_nature_first`
- `scenario_balanced`
- `scenario_low_conflict`

An undersized-cell penalty is applied so clipped coastal or boundary fragments do not dominate the shortlist.

## Scenario Score Summary

### Nature-first restoration opportunity

       scenario_nature_first
count               204703.0
mean                   45.33
std                     8.21
min                      0.0
25%                    41.89
50%                    45.56
75%                    48.56
max                    68.62

### Balanced restoration opportunity

       scenario_balanced
count           204703.0
mean               44.79
std                 8.77
min                  0.0
25%                40.34
50%                44.95
75%                47.98
max                71.56

### Lower-conflict restoration opportunity

       scenario_low_conflict
count               204703.0
mean                   40.09
std                    12.16
min                      0.0
25%                    31.16
50%                    41.01
75%                    43.21
max                    71.87

## Published Outputs From This Run

- Balanced top-100 shortlist summary: `outputs/top_candidates_1km/scenario_balanced_top_100_summary.md`
- Balanced candidate-zone summary: `outputs/candidate_clusters/scenario_balanced_top_100_clusters_summary.md`
- Validation summary: `outputs/validation/validation_summary.md`
- Standalone shortlist explorer: `outputs/app/rewilding_opportunity_explorer.html`

## Main Limitations

- Opportunity scores should not be read as proof of ecological outcomes.
- Agricultural opportunity remains a simplified tradeoff proxy rather than a full delivery-feasibility model.
- Flood and peat behavior depends on the active source data recorded in the run, and published outputs should only be treated as canonical when that run records dedicated sources.
- Observation-based biodiversity signals remain effort-sensitive and incomplete, even after simple record-coverage controls.
- Mammal records broaden the biodiversity dimension beyond birds, but both taxa remain shaped by recorder behavior and reporting intensity.
- High-ranking cells should be treated as candidate areas for follow-up, not final recommendations.

