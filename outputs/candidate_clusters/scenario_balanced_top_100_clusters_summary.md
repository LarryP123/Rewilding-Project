# Candidate Zones: scenario_balanced

Source layer: `data/interim/mvp_official_boundary_1km_v5/hex_scores.parquet`
Run profile: `canonical_published`
Flood source: `dedicated_dataset` from `data/interim/canonical_sources/ea_flood_zones_simplified.parquet`
Peat source: `dedicated_dataset` from `data/interim/canonical_sources/england_peat_map_simplified.parquet`
Top cells clustered: 100
Cluster distance: 20000 m

## Zone summary

 cluster_rank cluster_id  cell_count primary_lnrs_name lnrs_names lnrs_count  scenario_score_max  scenario_score_mean  habitat_share_mean  connectivity_mean  restoration_mean  agri_mean  centroid_easting_m  centroid_northing_m
            1 cluster_04          47              <NA>       <NA>       <NA>               71.56                70.58               78.89              99.87             99.08      100.0           471825.09            411030.74
            2 cluster_02          12              <NA>       <NA>       <NA>               68.44                67.72               80.03              99.64             98.84       80.0           344607.00            140069.33
            3 cluster_01          19              <NA>       <NA>       <NA>               68.37                67.07               74.49              99.71             98.97      100.0           237659.63             75339.68
            4 cluster_07          15              <NA>       <NA>       <NA>               68.02                67.22               91.14             100.00             99.09       80.0           546038.07            289061.13
            5 cluster_06           2              <NA>       <NA>       <NA>               67.68                67.39              100.00             100.00             99.00      100.0           377357.00            590358.50
            6 cluster_05           3              <NA>       <NA>       <NA>               67.57                67.06              100.00             100.00             99.00      100.0           395607.00            527223.33
            7 cluster_03           1              <NA>       <NA>       <NA>               66.83                66.83               39.09             100.00             99.61      100.0           344107.00            447719.00
            8 cluster_08           1              <NA>       <NA>       <NA>               66.76                66.76               34.60             100.00             99.65       80.0           647107.00            290791.00

## Top cells per zone

### cluster_04 (rank 1, 47 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0131578      <NA>              71.56                   85.33               100.0                          99.15
hex_0131394      <NA>              71.56                   76.84               100.0                          99.23
hex_0131521      <NA>              71.56                   82.99               100.0                          99.17
hex_0131522      <NA>              71.55                   99.54               100.0                          99.00
hex_0131519      <NA>              71.55                  100.00               100.0                          99.00

### cluster_02 (rank 2, 12 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0027388      <NA>              68.44                   99.63               100.0                           99.0
hex_0027445      <NA>              68.42                  100.00               100.0                           99.0
hex_0027273      <NA>              68.26                  100.00               100.0                           99.0
hex_0027387      <NA>              68.08                  100.00               100.0                           99.0
hex_0027102      <NA>              68.07                  100.00               100.0                           99.0

### cluster_01 (rank 3, 19 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0004231      <NA>              68.37                   21.15               98.62                          98.41
hex_0004129      <NA>              67.57                   14.37               98.33                          98.19
hex_0004234      <NA>              67.49                   65.76              100.00                          99.34
hex_0004628      <NA>              67.48                   95.38              100.00                          99.05
hex_0004128      <NA>              67.32                   60.68              100.00                          99.39

### cluster_07 (rank 4, 15 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0180983      <NA>              68.02                   99.78               100.0                          99.00
hex_0180866      <NA>              67.85                   92.63               100.0                          99.07
hex_0180514      <NA>               67.8                   94.56               100.0                          99.05
hex_0180631      <NA>              67.52                   99.79               100.0                          99.00
hex_0180455      <NA>               67.5                   94.79               100.0                          99.05

### cluster_06 (rank 5, 2 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0060095      <NA>              67.68                   100.0               100.0                           99.0
hex_0098401      <NA>              67.09                   100.0               100.0                           99.0

### cluster_05 (rank 6, 3 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0095576      <NA>              67.57                   100.0               100.0                           99.0
hex_0094345      <NA>              66.96                   100.0               100.0                           99.0
hex_0095011      <NA>              66.65                   100.0               100.0                           99.0

### cluster_03 (rank 7, 1 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0048297      <NA>              66.83                   39.09               100.0                          99.61

### cluster_08 (rank 8, 1 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0203619      <NA>              66.76                    34.6               100.0                          99.65

