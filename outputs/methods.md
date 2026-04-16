# Methods Note

## Purpose

This project is a national screening and prioritisation workflow for rewilding in England.
It combines a defined set of geospatial signals into comparable 1 km cell scores so England can be narrowed to plausible areas for closer review.
This is a screening tool, not a causal model, not a site-selection engine, and not a site-level recommendation.

## What This Run Does

The canonical run turns habitat, bird-observation, agricultural, flood, and peat-related signals into three scenario views over the same national hex grid.
Those scenario scores are then used to produce shortlist tables, candidate-zone summaries, validation outputs, and a standalone explorer.

## What This Run Does Not Claim

This run does not claim to identify final rewilding sites, predict ecological outcomes, model delivery feasibility, or replace local ecological and practical review.

## Canonical Run

- Canonical scored layer: `data/interim/mvp_official_boundary_1km_v4/hex_scores.parquet`
- Cells scored: 205,865
- Study area: England using the official England analysis boundary in British National Grid (`EPSG:27700`)
- Analysis unit: 1 km hexagonal grid cells

## Core Inputs In This Run

- Habitat context from the locally prepared habitat proxy used in the MVP workflow
- Flood opportunity source recorded in the score layer: `corine_proxy`
- Peat opportunity source recorded in the score layer: `corine_proxy`
- Agricultural opportunity from Agricultural Land Classification
- Bird observation opportunity from the observation-based bird indicator carried in this score layer

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
count               205865.0
mean                   44.01
std                     7.87
min                      0.0
25%                    40.72
50%                    44.53
75%                    47.88
max                    65.83

### Balanced restoration opportunity

       scenario_balanced
count           205865.0
mean               43.42
std                 8.47
min                  0.0
25%                39.14
50%                43.69
75%                47.45
max                70.28

### Lower-conflict restoration opportunity

       scenario_low_conflict
count               205865.0
mean                   39.17
std                     12.0
min                      0.0
25%                    29.98
50%                    40.28
75%                    43.05
max                    71.72

## Published Outputs From This Run

- Balanced top-100 shortlist summary: `outputs/top_candidates_1km/scenario_balanced_top_100_summary.md`
- Balanced candidate-zone summary: `outputs/candidate_clusters/scenario_balanced_top_100_clusters_summary.md`
- Validation summary: `outputs/validation/validation_summary.md`
- Standalone shortlist explorer: `outputs/app/rewilding_opportunity_explorer.html`

## Main Limitations

- Opportunity scores should not be read as proof of ecological outcomes.
- Agricultural opportunity remains a simplified tradeoff proxy rather than a full delivery-feasibility model.
- Flood and peat behavior depends on the active source data recorded in the run.
- Observation-based biodiversity signals remain effort-sensitive and incomplete.
- High-ranking cells should be treated as candidate areas for follow-up, not final recommendations.

