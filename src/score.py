from __future__ import annotations

import pandas as pd


SCENARIO_WEIGHTS = {
    "scenario_nature_first": {
        "restoration_opportunity_score": 0.45,
        "flood_opportunity_score_raw": 0.15,
        "peat_opportunity_score_raw": 0.15,
        "agri_opportunity_score_raw": 0.15,
        "habitat_mosaic_score": 0.10,
    },
    "scenario_balanced": {
        "restoration_opportunity_score": 0.35,
        "flood_opportunity_score_raw": 0.20,
        "peat_opportunity_score_raw": 0.15,
        "agri_opportunity_score_raw": 0.20,
        "habitat_mosaic_score": 0.10,
    },
    "scenario_low_conflict": {
        "restoration_opportunity_score": 0.20,
        "flood_opportunity_score_raw": 0.15,
        "peat_opportunity_score_raw": 0.10,
        "agri_opportunity_score_raw": 0.45,
        "habitat_mosaic_score": 0.10,
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


def add_restoration_opportunity_scores(
    frame: pd.DataFrame,
    habitat_share_column: str = "priority_habitat_share",
    connectivity_column: str = "connectivity_score",
) -> pd.DataFrame:
    """Create ecology features that favor restoration candidates over intact habitat.

    The key idea is:
    - cells very near habitat should score well,
    - cells already dominated by habitat should not automatically rank highest,
    - mixed cells near habitat can still be attractive restoration opportunities.
    """

    scored = frame.copy()
    habitat_share = scored[habitat_share_column].fillna(0).clip(lower=0, upper=100)
    connectivity = scored[connectivity_column].fillna(0).clip(lower=0, upper=100)

    # Reward cells that are near habitat but still have room for restoration.
    scored["restoration_opportunity_score"] = (
        connectivity * (1 - (habitat_share / 100))
    ).round(2)

    # Mildly favor habitat mosaics over both empty and already-fully-habitat cells.
    scored["habitat_mosaic_score"] = (
        100 - ((habitat_share - 20).abs() / 20 * 100)
    ).clip(lower=0, upper=100).round(2)

    return scored


def add_boundary_penalty(
    frame: pd.DataFrame,
    area_ratio_column: str = "cell_area_ratio",
    penalty_column: str = "undersized_cell_penalty",
    full_credit_threshold: float = 0.75,
) -> pd.DataFrame:
    """Down-rank heavily clipped cells near the analysis boundary.

    Cells that retain at least `full_credit_threshold` of a full hex keep their
    full score. Smaller fragments are scaled down linearly toward zero.
    """

    if full_credit_threshold <= 0 or full_credit_threshold > 1:
        raise ValueError("full_credit_threshold must be between 0 and 1.")

    scored = frame.copy()
    area_ratio = scored[area_ratio_column].fillna(0).clip(lower=0, upper=1)
    penalty = (area_ratio / full_credit_threshold).clip(lower=0, upper=1)
    scored[penalty_column] = penalty.round(4)
    return scored


def apply_scenarios(frame: pd.DataFrame, scenario_weights: dict[str, dict[str, float]] | None = None) -> pd.DataFrame:
    """Create scenario scores from weighted feature columns."""

    weights = scenario_weights or SCENARIO_WEIGHTS
    scored = frame.copy()
    penalty = scored.get("undersized_cell_penalty", 1.0)

    for scenario_name, scenario in weights.items():
        missing = [column for column in scenario if column not in scored.columns]
        if missing:
            raise KeyError(f"Missing columns for {scenario_name}: {missing}")

        total = sum(scored[column].fillna(0) * weight for column, weight in scenario.items())
        scored[scenario_name] = (total * penalty).round(2)

    return scored
