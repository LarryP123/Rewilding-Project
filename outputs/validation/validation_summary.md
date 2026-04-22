# Enriched Model Validation

Source layer: `data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet`
Shortlist size: top 100 cells
Run profile: `canonical_published`
Flood source: `dedicated_dataset` from `data/interim/canonical_sources/ea_flood_zones_simplified.parquet`
Peat source: `dedicated_dataset` from `data/interim/canonical_sources/england_peat_map_simplified.parquet`

## Scenario Stability

68 cells appear in the top 100 under all three scenario objectives.

| scenario_a | scenario_b | shared_cells | jaccard_overlap |
| --- | --- | --- | --- |
| scenario_nature_first | scenario_balanced | 94 | 0.887 |
| scenario_nature_first | scenario_low_conflict | 74 | 0.587 |
| scenario_balanced | scenario_low_conflict | 72 | 0.562 |

## Enriched vs Earlier Score Layer

| scenario | shared_cells | replaced_cells | shared_pct |
| --- | --- | --- | --- |
| scenario_nature_first | 0 | 100 | 0.0 |
| scenario_balanced | 0 | 100 | 0.0 |
| scenario_low_conflict | 1 | 99 | 1.0 |

## Weight Sensitivity

This perturbs the flood, peat, and biodiversity weights up and down while renormalising each scenario to 100%.

| scenario | min | mean | max |
| --- | --- | --- | --- |
| scenario_balanced | 82.0 | 92.0 | 100.0 |
| scenario_low_conflict | 92.0 | 95.0 | 99.0 |
| scenario_nature_first | 83.0 | 92.16666666666667 | 100.0 |

## Short Case Studies

### Consistently strong under all three objectives

- Hex: `hex_0131222`
- Area: Doncaster
- Why it matters: Ranks 4, 4, and 1 across the three scenarios; strongest signals are connectivity 100.0, lower agricultural conflict 100.0, peat opportunity 100.0.

### Moves up when peat, flood, and biodiversity matter more

- Hex: `hex_0008541`
- Area: Devon
- Why it matters: Nature-first rank 89 versus balanced rank 101; strongest signals are connectivity 100.0, lower agricultural conflict 100.0, peat opportunity 100.0.

### Useful where delivery feasibility matters most

- Hex: `hex_0023788`
- Area: Cumberland
- Why it matters: Low-conflict rank 61 versus balanced rank 124; strongest signals are connectivity 100.0, lower agricultural conflict 100.0, restoration opportunity 99.2.

