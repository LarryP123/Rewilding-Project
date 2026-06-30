# Nature Recovery Policy Explorer

## Day 3 Build File

This is the first scoring model:

`dbt/models/marts/fct_scenario_scores.sql`

The goal is to:

- join the base hex table to the seeded scenario weights
- calculate one weighted score per `hex_id` per `scenario_id`
- rank cells within each scenario
- assign a percentile for comparison views

## Input Models

This model depends on:

- `stg_hex_base`
- `scenario_weights` seed

## Output Shape

One row per `hex_id` per `scenario_id`.

Suggested columns:

- `hex_id`
- `admin_name`
- `geometry`
- `scenario_id`
- `scenario_label`
- `weighted_score`
- `national_rank`
- `percentile`
- `restoration_opportunity_score`
- `flood_opportunity_score_raw`
- `peat_opportunity_score_raw`
- `agri_opportunity_score_raw`
- `habitat_mosaic_score`
- `biodiversity_observation_score_raw`

## `fct_scenario_scores.sql`

Create:

`dbt/models/marts/fct_scenario_scores.sql`

```sql
with hex_base as (
    select *
    from {{ ref('stg_hex_base') }}
),

scenario_weights as (
    select
        scenario_id,
        scenario_label,
        component,
        cast(weight as double) as weight
    from {{ ref('scenario_weights') }}
),

long_scores as (
    select
        hex_id,
        admin_name,
        geometry,
        'restoration_opportunity_score' as component,
        restoration_opportunity_score as component_score
    from hex_base

    union all

    select
        hex_id,
        admin_name,
        geometry,
        'flood_opportunity_score_raw' as component,
        flood_opportunity_score_raw as component_score
    from hex_base

    union all

    select
        hex_id,
        admin_name,
        geometry,
        'peat_opportunity_score_raw' as component,
        peat_opportunity_score_raw as component_score
    from hex_base

    union all

    select
        hex_id,
        admin_name,
        geometry,
        'agri_opportunity_score_raw' as component,
        agri_opportunity_score_raw as component_score
    from hex_base

    union all

    select
        hex_id,
        admin_name,
        geometry,
        'habitat_mosaic_score' as component,
        habitat_mosaic_score as component_score
    from hex_base

    union all

    select
        hex_id,
        admin_name,
        geometry,
        'biodiversity_observation_score_raw' as component,
        biodiversity_observation_score_raw as component_score
    from hex_base
),

weighted as (
    select
        l.hex_id,
        l.admin_name,
        l.geometry,
        w.scenario_id,
        w.scenario_label,
        l.component,
        l.component_score,
        w.weight,
        l.component_score * w.weight as weighted_component_score
    from long_scores l
    inner join scenario_weights w
        on l.component = w.component
),

aggregated as (
    select
        hex_id,
        admin_name,
        geometry,
        scenario_id,
        scenario_label,
        sum(weighted_component_score) as weighted_score
    from weighted
    group by 1, 2, 3, 4, 5
),

rejoined_components as (
    select
        a.hex_id,
        a.admin_name,
        a.geometry,
        a.scenario_id,
        a.scenario_label,
        a.weighted_score,
        h.restoration_opportunity_score,
        h.flood_opportunity_score_raw,
        h.peat_opportunity_score_raw,
        h.agri_opportunity_score_raw,
        h.habitat_mosaic_score,
        h.biodiversity_observation_score_raw
    from aggregated a
    inner join hex_base h
        on a.hex_id = h.hex_id
),

ranked as (
    select
        *,
        row_number() over (
            partition by scenario_id
            order by weighted_score desc, hex_id
        ) as national_rank,
        percent_rank() over (
            partition by scenario_id
            order by weighted_score
        ) as percentile_from_bottom
    from rejoined_components
)

select
    hex_id,
    admin_name,
    geometry,
    scenario_id,
    scenario_label,
    round(weighted_score, 4) as weighted_score,
    national_rank,
    round((1 - percentile_from_bottom) * 100, 2) as percentile,
    restoration_opportunity_score,
    flood_opportunity_score_raw,
    peat_opportunity_score_raw,
    agri_opportunity_score_raw,
    habitat_mosaic_score,
    biodiversity_observation_score_raw
from ranked
```

## What This Model Does

1. Takes the base wide table and converts the six scoring components into a long format.
2. Joins those components to `scenario_weights`.
3. Calculates weighted component scores.
4. Aggregates them back to one row per `hex_id` and `scenario_id`.
5. Reattaches the original component scores for downstream explanation panels.
6. Ranks every cell within each scenario.

## Why The Long Join Pattern Is Useful

The important thing here is that the scenario logic lives in data, not in hardcoded `case when` blocks.

That means:

- scenario changes can happen in the seed file
- the scoring model stays generic
- adding a sixth scenario later is trivial
- front-end labels and metadata can be driven from the same source

## Optional Schema Test

Create:

`dbt/models/marts/fct_scenario_scores.yml`

```yaml
version: 2

models:
  - name: fct_scenario_scores
    columns:
      - name: hex_id
        tests:
          - not_null
      - name: scenario_id
        tests:
          - not_null
      - name: weighted_score
        tests:
          - not_null
      - name: national_rank
        tests:
          - not_null
      - name: percentile
        tests:
          - not_null
```

## Day 3 Commands

Run:

```bash
dbt run --project-dir dbt --select fct_scenario_scores
dbt test --project-dir dbt --select fct_scenario_scores
```

## Expected Day 3 Outcome

By the end of Day 3, you want:

- one scored row per hex per scenario
- scenario labels attached
- national ranking working
- percentile field ready for app filtering

That creates the first real analytical product in the new project.

## Next File After Day 3

The next model should be:

`dbt/models/marts/fct_scenario_comparison.sql`

That is where stable-core, scenario sensitivity, and rank spread get calculated.
