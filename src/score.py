from __future__ import annotations

import pandas as pd


SCENARIO_WEIGHTS = {
    "scenario_nature_first": {
        "priority_habitat_share": 0.35,
        "connectivity_score": 0.25,
        "flood_opportunity_score_raw": 0.15,
        "peat_opportunity_score_raw": 0.15,
        "agri_opportunity_score_raw": 0.10,
    },
    "scenario_balanced": {
        "priority_habitat_share": 0.25,
        "connectivity_score": 0.20,
        "flood_opportunity_score_raw": 0.20,
        "peat_opportunity_score_raw": 0.15,
        "agri_opportunity_score_raw": 0.20,
    },
    "scenario_low_conflict": {
        "priority_habitat_share": 0.20,
        "connectivity_score": 0.15,
        "flood_opportunity_score_raw": 0.15,
        "peat_opportunity_score_raw": 0.10,
        "agri_opportunity_score_raw": 0.40,
    },
}


def minmax_scale(series: pd.Series) -> pd.Series:
    """Scale numeric values to a 0-100 range."""

    non_null = series.dropna()
    if non_null.empty:
        return pd.Series([pd.NA] * len(series), index=series.index, dtype="Float64")

    min_value = non_null.min()
    max_value = non_null.max()
    if min_value == max_value:
        return pd.Series([100.0] * len(series), index=series.index, dtype="Float64")

    scaled = (series - min_value) / (max_value - min_value) * 100
    return scaled.astype("Float64")


def add_connectivity_score(
    frame: pd.DataFrame,
    distance_column: str = "distance_to_priority_habitat_m",
    feature_name: str = "connectivity_score",
) -> pd.DataFrame:
    """Convert habitat distance into a simple inverse connectivity score."""

    scored = frame.copy()
    max_distance = scored[distance_column].max()
    if pd.isna(max_distance) or max_distance == 0:
        scored[feature_name] = 100.0
        return scored

    scored[feature_name] = 100 - ((scored[distance_column] / max_distance) * 100)
    scored[feature_name] = scored[feature_name].clip(lower=0, upper=100)
    return scored


def apply_scenarios(frame: pd.DataFrame, scenario_weights: dict[str, dict[str, float]] | None = None) -> pd.DataFrame:
    """Create scenario scores from weighted feature columns."""

    weights = scenario_weights or SCENARIO_WEIGHTS
    scored = frame.copy()

    for scenario_name, scenario in weights.items():
        missing = [column for column in scenario if column not in scored.columns]
        if missing:
            raise KeyError(f"Missing columns for {scenario_name}: {missing}")

        total = sum(scored[column].fillna(0) * weight for column, weight in scenario.items())
        scored[scenario_name] = total.round(2)

    return scored
