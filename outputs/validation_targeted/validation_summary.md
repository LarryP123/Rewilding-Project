# Enriched Model Validation

Source layer: `data/interim/mvp_official_boundary_1km_targeted/hex_scores_targeted.parquet`
Shortlist size: top 100 cells

## Scenario Stability

41 cells appear in the top 100 under all three scenario objectives.

| scenario_a | scenario_b | shared_cells | jaccard_overlap |
| --- | --- | --- | --- |
| scenario_nature_first | scenario_balanced | 67 | 0.504 |
| scenario_nature_first | scenario_low_conflict | 43 | 0.274 |
| scenario_balanced | scenario_low_conflict | 63 | 0.46 |

## Enriched vs Earlier Score Layer

| scenario | shared_cells | replaced_cells | shared_pct |
| --- | --- | --- | --- |
| scenario_nature_first | 21 | 79 | 21.0 |
| scenario_balanced | 54 | 46 | 54.0 |
| scenario_low_conflict | 71 | 29 | 71.0 |

## Weight Sensitivity

This perturbs the flood, peat, and biodiversity weights up and down while renormalising each scenario to 100%.

| scenario | min | mean | max |
| --- | --- | --- | --- |
| scenario_balanced | 92.0 | 96.83333333333333 | 99.0 |
| scenario_low_conflict | 92.0 | 97.33333333333333 | 99.0 |
| scenario_nature_first | 82.0 | 95.16666666666667 | 100.0 |

## Short Case Studies

### Consistently strong under all three objectives

- Hex: `hex_0054754`
- Area: Blackburn with Darwen
- Why it matters: Ranks 1, 1, and 1 across the three scenarios; strongest signals are lower agricultural conflict 100.0, connectivity 98.2, restoration opportunity 84.5.

### Moves up when peat, flood, and biodiversity matter more

- Hex: `hex_0017898`
- Area: Devon
- Why it matters: Nature-first rank 4 versus balanced rank 197; strongest signals are connectivity 99.0, restoration opportunity 86.2, lower agricultural conflict 80.0.

### Useful where delivery feasibility matters most

- Hex: `hex_0024204`
- Area: Cumberland
- Why it matters: Low-conflict rank 42 versus balanced rank 119; strongest signals are lower agricultural conflict 100.0, connectivity 99.0, biodiversity proxy 77.4.

