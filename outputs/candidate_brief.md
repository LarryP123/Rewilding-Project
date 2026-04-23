# Candidate Brief: Balanced restoration opportunity

## Overview

This brief summarises the leading areas from the balanced restoration opportunity scenario.
The current top 100 cells resolve into 11 candidate zones, but the shortlist is not evenly spread.
The top 3 zones contain 42 of the top 100 cells, which means the analysis is already pointing toward a small number of coherent priority areas rather than isolated one-off winners.

## At A Glance

- Main scenario: Balanced restoration opportunity
- Shortlist scale: top 100 1 km cells grouped into 11 candidate zones
- Dominant pattern: the top 3 zones account for 42% of the shortlist by cell count
- Leading named areas: Northern Eastern Zone (Nottinghamshire), Southern Western Zone (Somerset), Southwest Peninsula (Cornwall)
- Source layer: `data/interim/mvp_official_boundary_1km_v6/hex_scores.parquet`
- Run profile: `canonical_published`

## Leading Zones

### 1. Northern Eastern Zone (Nottinghamshire)

A broader candidate zone that sits outside the three main core areas.

- Cells in zone: 6
- Max score: 67.04
- Mean score: 64.38
- Mean habitat share: 3.32%
- Mean connectivity: 96.69
- Mean restoration score: 93.43
- Mean ALC opportunity: 86.67
- Primary LNRS: Not assigned
- LNRS coverage in zone: Not assigned
- County / unitary authority: Nottinghamshire

### 2. Southern Western Zone (Somerset)

A broader candidate zone that sits outside the three main core areas.

- Cells in zone: 5
- Max score: 66.99
- Mean score: 64.23
- Mean habitat share: 0.42%
- Mean connectivity: 95.31
- Mean restoration score: 94.90
- Mean ALC opportunity: 80.00
- Primary LNRS: Not assigned
- LNRS coverage in zone: Not assigned
- County / unitary authority: Somerset

### 3. Southwest Peninsula (Cornwall)

Compact southwestern cluster with strong restoration scores and a coastal-peninsula setting.

- Cells in zone: 31
- Max score: 66.93
- Mean score: 64.10
- Mean habitat share: 9.89%
- Mean connectivity: 98.03
- Mean restoration score: 88.25
- Mean ALC opportunity: 94.84
- Primary LNRS: Not assigned
- LNRS coverage in zone: Not assigned
- County / unitary authority: Cornwall

## Interpretation

The leading zones are being driven by cells that sit very near existing habitat, retain room for restoration rather than already being fully habitat-dominated, and carry high agricultural opportunity scores.
That pattern is consistent across the top-ranked areas, which is a good sign that the current ranking is producing a repeatable signal rather than random local noise.

## What This Is

This is a first national prioritisation pass, not a site-level recommendation. The outputs are most useful for narrowing England down to a manageable shortlist of areas for closer ecological and practical review.

## Core Files

- Canonical release checkpoint: `outputs/release/canonical_v6.json`
- Shortlist explorer app: `outputs/app/rewilding_opportunity_explorer.html`
- Inspection map: `outputs/maps/scenario_balanced_top_100_map.html`
- Methods note: `outputs/methods.md`
- Cluster summary CSV: `outputs/candidate_clusters/scenario_balanced_top_100_clusters.csv`
- Cluster summary markdown: `outputs/candidate_clusters/scenario_balanced_top_100_clusters_summary.md`

