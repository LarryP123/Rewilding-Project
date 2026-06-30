with comparison as (
    select *
    from {{ ref('fct_scenario_comparison') }}
)

select
    hex_id,
    geometry,
    best_scenario_id,
    best_scenario_label,
    best_weighted_score,
    worst_scenario_id,
    worst_scenario_label,
    worst_weighted_score,
    best_rank,
    worst_rank,
    rank_spread,
    best_percentile,
    worst_percentile,
    top_decile_scenario_count,
    stable_core_flag,
    contested_flag,
    restoration_opportunity_score,
    flood_opportunity_score_raw,
    peat_opportunity_score_raw,
    agri_opportunity_score_raw,
    habitat_mosaic_score,
    biodiversity_observation_score_raw,
    balanced_strategy_weighted_score,
    balanced_strategy_rank,
    balanced_strategy_percentile,
    carbon_restoration_weighted_score,
    carbon_restoration_rank,
    carbon_restoration_percentile,
    flood_resilience_weighted_score,
    flood_resilience_rank,
    flood_resilience_percentile,
    lower_conflict_weighted_score,
    lower_conflict_rank,
    lower_conflict_percentile,
    nature_recovery_weighted_score,
    nature_recovery_rank,
    nature_recovery_percentile
from comparison
