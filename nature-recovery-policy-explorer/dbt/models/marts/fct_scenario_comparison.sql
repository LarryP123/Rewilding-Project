with scenario_scores as (
    select *
    from {{ ref('fct_scenario_scores') }}
),

scenario_counts as (
    select count(distinct scenario_id) as scenario_count
    from scenario_scores
),

per_hex as (
    select
        hex_id,
        any_value(geometry) as geometry,
        any_value(priority_habitat_share) as priority_habitat_share,
        any_value(distance_to_priority_habitat_m) as distance_to_priority_habitat_m,
        any_value(agri_opportunity_score_raw) as agri_opportunity_score_raw,
        any_value(flood_opportunity_score_raw) as flood_opportunity_score_raw,
        any_value(peat_opportunity_score_raw) as peat_opportunity_score_raw,
        any_value(connectivity_score) as connectivity_score,
        any_value(undersized_cell_penalty) as undersized_cell_penalty,
        any_value(cell_area_ratio) as cell_area_ratio,
        any_value(restoration_opportunity_score) as restoration_opportunity_score,
        any_value(habitat_mosaic_score) as habitat_mosaic_score,
        any_value(biodiversity_observation_score_raw) as biodiversity_observation_score_raw,
        any_value(bird_observation_score_raw) as bird_observation_score_raw,
        any_value(mammal_observation_score_raw) as mammal_observation_score_raw,
        any_value(bird_species_richness) as bird_species_richness,
        any_value(bird_record_count) as bird_record_count,
        any_value(mammal_species_richness) as mammal_species_richness,
        any_value(mammal_record_count) as mammal_record_count,
        any_value(flood_feature_source) as flood_feature_source,
        any_value(peat_feature_source) as peat_feature_source,
        any_value(run_profile) as run_profile,
        min(national_rank) as best_rank,
        max(national_rank) as worst_rank,
        min(percentile) as worst_percentile,
        max(percentile) as best_percentile,
        max(national_rank) - min(national_rank) as rank_spread,
        count_if(percentile >= 90) as top_decile_scenario_count
    from scenario_scores
    group by 1
),

best_scenario as (
    select
        hex_id,
        scenario_id as best_scenario_id,
        scenario_label as best_scenario_label,
        weighted_score as best_weighted_score
    from scenario_scores
    qualify row_number() over (
        partition by hex_id
        order by national_rank asc, scenario_id
    ) = 1
),

worst_scenario as (
    select
        hex_id,
        scenario_id as worst_scenario_id,
        scenario_label as worst_scenario_label,
        weighted_score as worst_weighted_score
    from scenario_scores
    qualify row_number() over (
        partition by hex_id
        order by national_rank desc, scenario_id
    ) = 1
),

wide_scores as (
    select
        hex_id,
        max(case when scenario_id = 'balanced_strategy' then weighted_score end) as balanced_strategy_weighted_score,
        max(case when scenario_id = 'balanced_strategy' then national_rank end) as balanced_strategy_rank,
        max(case when scenario_id = 'balanced_strategy' then percentile end) as balanced_strategy_percentile,
        max(case when scenario_id = 'carbon_restoration' then weighted_score end) as carbon_restoration_weighted_score,
        max(case when scenario_id = 'carbon_restoration' then national_rank end) as carbon_restoration_rank,
        max(case when scenario_id = 'carbon_restoration' then percentile end) as carbon_restoration_percentile,
        max(case when scenario_id = 'flood_resilience' then weighted_score end) as flood_resilience_weighted_score,
        max(case when scenario_id = 'flood_resilience' then national_rank end) as flood_resilience_rank,
        max(case when scenario_id = 'flood_resilience' then percentile end) as flood_resilience_percentile,
        max(case when scenario_id = 'lower_conflict' then weighted_score end) as lower_conflict_weighted_score,
        max(case when scenario_id = 'lower_conflict' then national_rank end) as lower_conflict_rank,
        max(case when scenario_id = 'lower_conflict' then percentile end) as lower_conflict_percentile,
        max(case when scenario_id = 'nature_recovery' then weighted_score end) as nature_recovery_weighted_score,
        max(case when scenario_id = 'nature_recovery' then national_rank end) as nature_recovery_rank,
        max(case when scenario_id = 'nature_recovery' then percentile end) as nature_recovery_percentile
    from scenario_scores
    group by 1
)

select
    h.hex_id,
    h.geometry,
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
    b.best_scenario_id,
    b.best_scenario_label,
    round(b.best_weighted_score, 4) as best_weighted_score,
    w.worst_scenario_id,
    w.worst_scenario_label,
    round(w.worst_weighted_score, 4) as worst_weighted_score,
    h.best_rank,
    h.worst_rank,
    h.rank_spread,
    round(h.best_percentile, 2) as best_percentile,
    round(h.worst_percentile, 2) as worst_percentile,
    h.top_decile_scenario_count,
    case
        when h.top_decile_scenario_count = c.scenario_count then true
        else false
    end as stable_core_flag,
    case
        when h.top_decile_scenario_count > 0
         and h.top_decile_scenario_count < c.scenario_count then true
        else false
    end as contested_flag,
    round(s.balanced_strategy_weighted_score, 4) as balanced_strategy_weighted_score,
    s.balanced_strategy_rank,
    round(s.balanced_strategy_percentile, 2) as balanced_strategy_percentile,
    round(s.carbon_restoration_weighted_score, 4) as carbon_restoration_weighted_score,
    s.carbon_restoration_rank,
    round(s.carbon_restoration_percentile, 2) as carbon_restoration_percentile,
    round(s.flood_resilience_weighted_score, 4) as flood_resilience_weighted_score,
    s.flood_resilience_rank,
    round(s.flood_resilience_percentile, 2) as flood_resilience_percentile,
    round(s.lower_conflict_weighted_score, 4) as lower_conflict_weighted_score,
    s.lower_conflict_rank,
    round(s.lower_conflict_percentile, 2) as lower_conflict_percentile,
    round(s.nature_recovery_weighted_score, 4) as nature_recovery_weighted_score,
    s.nature_recovery_rank,
    round(s.nature_recovery_percentile, 2) as nature_recovery_percentile
from per_hex h
cross join scenario_counts c
inner join best_scenario b
    on h.hex_id = b.hex_id
inner join worst_scenario w
    on h.hex_id = w.hex_id
inner join wide_scores s
    on h.hex_id = s.hex_id
