# Top Candidates: scenario_balanced

Source layer: `data/interim/mvp_official_boundary_1km_v6/hex_scores.parquet`
Run profile: `canonical_published`
Flood source: `dedicated_dataset` from `data/interim/canonical_sources/ea_flood_zones_simplified.parquet`
Peat source: `dedicated_dataset` from `data/interim/canonical_sources/england_peat_map_simplified.parquet`
Rows exported: 100

## Score summary

       scenario_balanced
count              100.0
mean               63.44
std                 1.26
min                62.01
25%                62.48
50%                63.05
75%                64.07
max                67.04

## Top 10 hexes

     hex_id lnrs_name  scenario_balanced  cell_area_ratio  undersized_cell_penalty  priority_habitat_share  connectivity_score  restoration_opportunity_score  biodiversity_observation_score_raw  bird_species_richness  bird_record_count  mammal_species_richness  mammal_record_count  habitat_mosaic_score  agri_opportunity_score_raw
hex_0131453      <NA>              67.04              1.0                      1.0                    0.00               96.69                          96.69                                 0.0                    0.0                0.0                      0.0                  0.0                  0.00                       100.0
hex_0027562      <NA>              66.99              1.0                      1.0                    0.00               95.73                          95.73                                 0.0                    0.0                0.0                      0.0                  0.0                  0.00                        80.0
hex_0004129      <NA>              66.93              1.0                      1.0                   14.37               98.33                          84.20                                 0.0                    0.0                0.0                      0.0                  0.0                 71.83                       100.0
hex_0004231      <NA>              66.83              1.0                      1.0                   21.15               98.62                          77.76                                 0.0                    0.0                0.0                      0.0                  0.0                 94.25                       100.0
hex_0004180      <NA>               66.3              1.0                      1.0                    6.12               98.15                          92.15                                 0.0                    0.0                0.0                      0.0                  0.0                 30.61                        80.0
hex_0131452      <NA>              66.09              1.0                      1.0                   12.98               98.15                          85.40                                 0.0                    0.0                0.0                      0.0                  0.0                 64.92                       100.0
hex_0004286      <NA>              65.93              1.0                      1.0                   16.17               98.11                          82.25                                 0.0                    0.0                0.0                      0.0                  0.0                 80.83                       100.0
hex_0009053      <NA>              65.43              1.0                      1.0                    9.90               98.51                          88.75                                 0.0                    0.0                0.0                      0.0                  0.0                 49.50                       100.0
hex_0009396      <NA>              65.35              1.0                      1.0                    0.00               96.10                          96.10                                 0.0                    0.0                0.0                      0.0                  0.0                  0.00                       100.0
hex_0004179      <NA>              65.34              1.0                      1.0                    0.00               96.42                          96.42                                 0.0                    0.0                0.0                      0.0                  0.0                  0.00                       100.0
