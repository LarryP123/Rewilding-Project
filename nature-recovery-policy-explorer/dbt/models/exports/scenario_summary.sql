with scenario_scores as (
    select *
    from {{ ref('fct_scenario_scores') }}
),

scenario_counts as (
    select count(distinct scenario_id) as scenario_count
    from scenario_scores
),

stable_core as (
    select count(*) as stable_core_hex_count
    from {{ ref('fct_scenario_comparison') }}
    where stable_core_flag
),

contested as (
    select count(*) as contested_hex_count
    from {{ ref('fct_scenario_comparison') }}
    where contested_flag
)

select
    s.scenario_id,
    any_value(s.scenario_label) as scenario_label,
    count(*) as hex_count,
    min(s.weighted_score) as min_weighted_score,
    max(s.weighted_score) as max_weighted_score,
    avg(s.weighted_score) as avg_weighted_score,
    min(s.national_rank) as best_rank,
    max(s.national_rank) as worst_rank,
    avg(s.percentile) as avg_percentile,
    count_if(s.percentile >= 90) as top_decile_hex_count,
    count_if(s.percentile >= 95) as top_5_percent_hex_count,
    count_if(s.percentile >= 99) as top_1_percent_hex_count,
    cast(any_value(sc.stable_core_hex_count) as bigint) as stable_core_hex_count,
    cast(any_value(c.contested_hex_count) as bigint) as contested_hex_count,
    cast(any_value(cnt.scenario_count) as bigint) as scenario_count
from scenario_scores s
cross join stable_core sc
cross join contested c
cross join scenario_counts cnt
group by 1
order by scenario_id
