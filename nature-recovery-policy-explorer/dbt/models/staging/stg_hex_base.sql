with source as (
    select *
    from read_parquet('data/raw/hex_base_source.parquet')
),

renamed as (
    select
        cast(hex_id as varchar) as hex_id,
        cast(priority_habitat_share as double) as priority_habitat_share,
        cast(distance_to_priority_habitat_m as double) as distance_to_priority_habitat_m,
        cast(agri_opportunity_score_raw as double) as agri_opportunity_score_raw,
        cast(flood_opportunity_score_raw as double) as flood_opportunity_score_raw,
        cast(peat_opportunity_score_raw as double) as peat_opportunity_score_raw,
        cast(connectivity_score as double) as connectivity_score,
        cast(undersized_cell_penalty as double) as undersized_cell_penalty,
        cast(cell_area_ratio as double) as cell_area_ratio,
        cast(restoration_opportunity_score as double) as restoration_opportunity_score,
        cast(habitat_mosaic_score as double) as habitat_mosaic_score,
        cast(biodiversity_observation_score_raw as double) as biodiversity_observation_score_raw,
        cast(bird_observation_score_raw as double) as bird_observation_score_raw,
        cast(mammal_observation_score_raw as double) as mammal_observation_score_raw,
        cast(bird_species_richness as double) as bird_species_richness,
        cast(bird_record_count as double) as bird_record_count,
        cast(mammal_species_richness as double) as mammal_species_richness,
        cast(mammal_record_count as double) as mammal_record_count,
        cast(scenario_nature_first as double) as scenario_nature_first,
        cast(scenario_balanced as double) as scenario_balanced,
        cast(scenario_low_conflict as double) as scenario_low_conflict,
        flood_feature_source,
        peat_feature_source,
        run_profile,
        geometry
    from source
),

deduplicated as (
    select *
    from renamed
    qualify row_number() over (
        partition by hex_id
        order by
            scenario_balanced desc nulls last,
            restoration_opportunity_score desc nulls last,
            biodiversity_observation_score_raw desc nulls last
    ) = 1
)

select *
from deduplicated
