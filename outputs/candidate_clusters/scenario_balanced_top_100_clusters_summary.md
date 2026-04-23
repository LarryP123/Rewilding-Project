# Candidate Zones: scenario_balanced

Source layer: `data/interim/mvp_official_boundary_1km_v6/hex_scores.parquet`
Run profile: `canonical_published`
Flood source: `dedicated_dataset` from `data/interim/canonical_sources/ea_flood_zones_simplified.parquet`
Peat source: `dedicated_dataset` from `data/interim/canonical_sources/england_peat_map_simplified.parquet`
Top cells clustered: 100
Cluster distance: 20000 m

## Zone summary

 cluster_rank cluster_id  cell_count primary_lnrs_name lnrs_names lnrs_count  scenario_score_max  scenario_score_mean  habitat_share_mean  connectivity_mean  restoration_mean  agri_mean  centroid_easting_m  centroid_northing_m
            1 cluster_10           6              <NA>       <NA>       <NA>               67.04                64.38                3.32              96.69             93.43      86.67           472315.33            407924.83
            2 cluster_05           5              <NA>       <NA>       <NA>               66.99                64.23                0.42              95.31             94.90      80.00           347107.00            141830.20
            3 cluster_01          31              <NA>       <NA>       <NA>               66.93                 64.1                9.89              98.03             88.25      94.84           241808.61             76529.94
            4 cluster_02          17              <NA>       <NA>       <NA>               64.91                63.17                3.31              97.18             93.93     100.00           277048.18            138804.29
            5 cluster_07           8              <NA>       <NA>       <NA>               64.22                63.04                9.72              98.32             88.73     100.00           394107.00            581077.00
            6 cluster_03          17              <NA>       <NA>       <NA>               64.03                 62.7                9.32              96.73             87.51      97.65           380680.53            443564.35
            7 cluster_08           7              <NA>       <NA>       <NA>               63.68                62.76                7.91              96.33             88.48      78.57           564142.71            276130.86
            8 cluster_09           4              <NA>       <NA>       <NA>               63.67                63.04                3.35              93.05             89.72      80.00           637923.75            299706.75
            9 cluster_11           2              <NA>       <NA>       <NA>               63.35                62.88                3.13              97.82             94.74     100.00           486232.00            493605.50
           10 cluster_06           2              <NA>       <NA>       <NA>               63.24                63.11                7.30              98.56             91.29      80.00           362482.00            327584.50
           11 cluster_04           1              <NA>       <NA>       <NA>               62.12                62.12                0.00              81.52             81.52     100.00           315107.00            546853.00

## Top cells per zone

### cluster_10 (rank 1, 6 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0131453      <NA>              67.04                    0.00               96.69                          96.69
hex_0131452      <NA>              66.09                   12.98               98.15                          85.40
hex_0127366      <NA>              65.02                    0.00               96.93                          96.93
hex_0162208      <NA>              63.45                    0.00               96.09                          96.09
hex_0127123      <NA>              62.51                    0.00               94.19                          94.19

### cluster_05 (rank 2, 5 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0027562      <NA>              66.99                    0.00               95.73                          95.73
hex_0027449      <NA>              64.97                    2.08               97.81                          95.77
hex_0027619      <NA>              63.64                    0.00               92.40                          92.40
hex_0027505      <NA>              63.04                    0.00               95.54                          95.54
hex_0027391      <NA>              62.51                    0.00               95.08                          95.08

### cluster_01 (rank 3, 31 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0004129      <NA>              66.93                   14.37               98.33                          84.20
hex_0004231      <NA>              66.83                   21.15               98.62                          77.76
hex_0004180      <NA>               66.3                    6.12               98.15                          92.15
hex_0004286      <NA>              65.93                   16.17               98.11                          82.25
hex_0009053      <NA>              65.43                    9.90               98.51                          88.75

### cluster_02 (rank 4, 17 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0013344      <NA>              64.91                    7.82               98.08                          90.42
hex_0012816      <NA>              64.53                    0.11               97.05                          96.94
hex_0012762      <NA>              64.34                    2.31               97.67                          95.41
hex_0013331      <NA>               63.9                    0.00               96.18                          96.18
hex_0012869      <NA>              63.55                    2.43               97.82                          95.44

### cluster_07 (rank 5, 8 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0103556      <NA>              64.22                   13.27               98.22                          85.19
hex_0097921      <NA>               64.1                    7.11               98.22                          91.24
hex_0097862      <NA>              63.09                   10.37               98.45                          88.24
hex_0098444      <NA>              63.06                   20.37               99.62                          79.33
hex_0098618      <NA>              62.62                    0.00               96.83                          96.83

### cluster_03 (rank 6, 17 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0053582      <NA>              64.03                   11.10               99.57                          88.52
hex_0091822      <NA>               63.7                   15.31               98.86                          83.73
hex_0051858      <NA>               63.6                   12.42               98.77                          86.50
hex_0048089      <NA>              63.52                    0.00               83.06                          83.06
hex_0090796      <NA>              63.04                   19.78               98.70                          79.18

### cluster_08 (rank 7, 7 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0182357      <NA>              63.68                   15.03               98.44                          83.64
hex_0181014      <NA>              62.96                    0.00               92.65                          92.65
hex_0182571      <NA>              62.74                    0.00               96.64                          96.64
hex_0179693      <NA>              62.74                    0.00               93.75                          93.75
hex_0182686      <NA>              62.47                   19.12               99.52                          80.49

### cluster_09 (rank 8, 4 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0204085      <NA>              63.67                   13.39               99.54                          86.21
hex_0202989      <NA>              62.97                    0.00               90.33                          90.33
hex_0203046      <NA>              62.92                    0.00               95.76                          95.76
hex_0202931      <NA>              62.62                    0.00               86.57                          86.57

### cluster_11 (rank 9, 2 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0165555      <NA>              63.35                    6.26               98.39                          92.23
hex_0165610      <NA>               62.4                    0.00               97.24                          97.24

### cluster_06 (rank 10, 2 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0041198      <NA>              63.24                   14.18               99.70                          85.57
hex_0043288      <NA>              62.98                    0.43               97.42                          97.01

### cluster_04 (rank 11, 1 cells)

     hex_id lnrs_name  scenario_balanced  priority_habitat_share  connectivity_score  restoration_opportunity_score
hex_0023180      <NA>              62.12                     0.0               81.52                          81.52

