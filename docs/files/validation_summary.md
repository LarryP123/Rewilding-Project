# Enriched Model Validation

Source layer: `data/interim/mvp_official_boundary_1km_v6/hex_scores.parquet`
Shortlist size: top 100 cells
Run profile: `canonical_published`
Flood source: `dedicated_dataset` from `data/interim/canonical_sources/ea_flood_zones_simplified.parquet`
Peat source: `dedicated_dataset` from `data/interim/canonical_sources/england_peat_map_simplified.parquet`

## Scenario Stability

36 cells appear in the top 100 under all three scenario objectives.

| scenario_a | scenario_b | shared_cells | jaccard_overlap |
| --- | --- | --- | --- |
| scenario_nature_first | scenario_balanced | 84 | 0.724 |
| scenario_nature_first | scenario_low_conflict | 36 | 0.22 |
| scenario_balanced | scenario_low_conflict | 46 | 0.299 |

## Enriched vs Earlier Score Layer

| scenario | shared_cells | replaced_cells | shared_pct |
| --- | --- | --- | --- |
| scenario_nature_first | 0 | 100 | 0.0 |
| scenario_balanced | 0 | 100 | 0.0 |
| scenario_low_conflict | 0 | 100 | 0.0 |

## Weight Sensitivity

This perturbs the flood, peat, and biodiversity weights up and down while renormalising each scenario to 100%.

| scenario | min | mean | max |
| --- | --- | --- | --- |
| scenario_balanced | 91.0 | 95.16666666666667 | 100.0 |
| scenario_low_conflict | 93.0 | 96.83333333333333 | 99.0 |
| scenario_nature_first | 90.0 | 95.0 | 100.0 |

## Short Case Studies

### Consistently strong under all three objectives

- Hex: `hex_0004129`
- Area: Cornwall
- Why it matters: Ranks 4, 3, and 2 across the three scenarios; strongest signals are lower agricultural conflict 100.0, connectivity 98.3, peat opportunity 85.1.

### Moves up when peat, flood, and biodiversity matter more

- Hex: `hex_0027105`
- Area: Somerset
- Why it matters: Nature-first rank 46 versus balanced rank 105; strongest signals are restoration opportunity 96.7, connectivity 96.7, peat opportunity 92.4.

### Useful where delivery feasibility matters most

- Hex: `hex_0046503`
- Area: Wigan
- Why it matters: Low-conflict rank 26 versus balanced rank 133; strongest signals are lower agricultural conflict 100.0, connectivity 98.9, habitat mosaic 95.9.

