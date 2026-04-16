from __future__ import annotations

import pandas as pd
import pytest

from src.score import (
    add_bird_observation_scores,
    add_boundary_penalty,
    add_connectivity_score,
    add_restoration_opportunity_scores,
    apply_scenarios,
)


def test_apply_scenarios_stays_within_expected_score_range() -> None:
    frame = pd.DataFrame(
        {
            "distance_to_priority_habitat_m": [0.0, 25.0, 100.0],
            "priority_habitat_share": [10.0, 30.0, 70.0],
            "bird_species_richness": [1, 3, 5],
            "bird_record_count": [5, 15, 25],
            "flood_opportunity_score_raw": [20.0, 50.0, 80.0],
            "peat_opportunity_score_raw": [10.0, 30.0, 60.0],
            "agri_opportunity_score_raw": [40.0, 60.0, 90.0],
            "cell_area_ratio": [1.0, 0.75, 0.20],
        }
    )

    frame = add_connectivity_score(frame)
    frame = add_restoration_opportunity_scores(frame)
    frame = add_boundary_penalty(frame)
    frame = add_bird_observation_scores(frame)
    frame = apply_scenarios(frame)

    for scenario_name in ("scenario_nature_first", "scenario_balanced", "scenario_low_conflict"):
        assert frame[scenario_name].between(0, 100).all()


def test_boundary_penalty_rejects_invalid_thresholds() -> None:
    frame = pd.DataFrame({"cell_area_ratio": [0.25, 0.75, 1.0]})

    with pytest.raises(ValueError):
        add_boundary_penalty(frame, full_credit_threshold=0)

    with pytest.raises(ValueError):
        add_boundary_penalty(frame, full_credit_threshold=1.5)


def test_boundary_penalty_scales_clipped_cells_linearly() -> None:
    frame = pd.DataFrame({"cell_area_ratio": [1.0, 0.75, 0.375, 0.0]})

    result = add_boundary_penalty(frame, full_credit_threshold=0.75)

    assert list(result["undersized_cell_penalty"]) == [1.0, 1.0, 0.5, 0.0]
