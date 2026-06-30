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
        geometry,
        'restoration_opportunity_score' as component,
        restoration_opportunity_score as component_score
    from hex_base

    union all

    select
        hex_id,
        geometry,
        'flood_opportunity_score_raw' as component,
        flood_opportunity_score_raw as component_score
    from hex_base

    union all

    select
        hex_id,
        geometry,
        'peat_opportunity_score_raw' as component,
        peat_opportunity_score_raw as component_score
    from hex_base

    union all

    select
        hex_id,
        geometry,
        'agri_opportunity_score_raw' as component,
        agri_opportunity_score_raw as component_score
    from hex_base

    union all

    select
        hex_id,
        geometry,
        'habitat_mosaic_score' as component,
        habitat_mosaic_score as component_score
    from hex_base

    union all

    select
        hex_id,
        geometry,
        'biodiversity_observation_score_raw' as component,
        biodiversity_observation_score_raw as component_score
    from hex_base
),

weighted as (
    select
        l.hex_id,
        l.geometry,
        w.scenario_id,
        w.scenario_label,
        l.component,
        cast(l.component_score as double) as component_score,
        w.weight,
        cast(l.component_score as double) * w.weight as weighted_component_score
    from long_scores l
    inner join scenario_weights w
        on l.component = w.component
),

aggregated as (
    select
        hex_id,
        geometry,
        scenario_id,
        scenario_label,
        sum(weighted_component_score) as weighted_score
    from weighted
    group by 1, 2, 3, 4
),

rejoined_components as (
    select
        a.hex_id,
        h.priority_habitat_share,
        h.distance_to_priority_habitat_m,
        h.agri_opportunity_score_raw,
        h.flood_opportunity_score_raw,
        h.peat_opportunity_score_raw,
        h.connectivity_score,
        h.undersized_cell_penalty,
        h.cell_area_ratio,
        h.restoration_opportunity_score,
        h.habitat_mosaic_score,
        h.biodiversity_observation_score_raw,
        h.bird_observation_score_raw,
        h.mammal_observation_score_raw,
        h.bird_species_richness,
        h.bird_record_count,
        h.mammal_species_richness,
        h.mammal_record_count,
        h.flood_feature_source,
        h.peat_feature_source,
        h.run_profile,
        a.geometry,
        a.scenario_id,
        a.scenario_label,
        a.weighted_score
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
    priority_habitat_share,
    distance_to_priority_habitat_m,
    agri_opportunity_score_raw,
    flood_opportunity_score_raw,
    peat_opportunity_score_raw,
    connectivity_score,
    undersized_cell_penalty,
    cell_area_ratio,
    restoration_opportunity_score,
    habitat_mosaic_score,
    biodiversity_observation_score_raw,
    bird_observation_score_raw,
    mammal_observation_score_raw,
    bird_species_richness,
    bird_record_count,
    mammal_species_richness,
    mammal_record_count,
    flood_feature_source,
    peat_feature_source,
    run_profile,
    geometry,
    scenario_id,
    scenario_label,
    round(weighted_score, 4) as weighted_score,
    national_rank,
    round((1 - percentile_from_bottom) * 100, 2) as percentile
from ranked
