# Enriched Model Validation

Source layer: `data/interim/mvp_official_boundary_1km_v4/hex_scores.parquet`
Shortlist size: top 100 cells

## Scenario Stability

52 cells appear in the top 100 under all three scenario objectives.

| scenario_a | scenario_b | shared_cells | jaccard_overlap |
| --- | --- | --- | --- |
| scenario_nature_first | scenario_balanced | 57 | 0.399 |
| scenario_nature_first | scenario_low_conflict | 55 | 0.379 |
| scenario_balanced | scenario_low_conflict | 93 | 0.869 |

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
| scenario_balanced | 43.0 | 66.16666666666667 | 97.0 |
| scenario_low_conflict | 81.0 | 90.66666666666667 | 97.0 |
| scenario_nature_first | 65.0 | 88.16666666666667 | 99.0 |

## Short Case Studies

### Consistently strong under all three objectives

- Hex: `hex_0077601`
- Area: North Yorkshire
- Why it matters: Ranks 1, 43, and 46 across the three scenarios; strongest signals are connectivity 100.0, lower agricultural conflict 100.0, peat opportunity 100.0.

### Moves up when peat, flood, and biodiversity matter more

- Hex: `hex_0054698`
- Area: Blackburn with Darwen
- Why it matters: Nature-first rank 50 versus balanced rank 95; strongest signals are habitat share 100.0, connectivity 100.0, lower agricultural conflict 100.0.

### Useful where delivery feasibility matters most

- Hex: `hex_0021003`
- Area: Cheshire West and Chester
- Why it matters: Low-conflict rank 41 versus balanced rank 153; strongest signals are connectivity 100.0, lower agricultural conflict 100.0, restoration opportunity 99.1.

