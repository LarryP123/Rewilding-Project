from __future__ import annotations

import pandas as pd
import pytest

from src.score import (
    add_biodiversity_observation_score,
    add_bird_observation_scores,
    add_boundary_penalty,
    add_connectivity_score,
    add_mammal_observation_scores,
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
            "mammal_species_richness": [0, 2, 4],
            "mammal_record_count": [0, 5, 15],
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
    frame = add_mammal_observation_scores(frame)
    frame = add_biodiversity_observation_score(frame)
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


def test_biodiversity_observation_score_combines_taxa_and_effort_controls() -> None:
    frame = pd.DataFrame(
        {
            "bird_species_richness": [1, 5],
            "bird_record_count": [2, 25],
            "mammal_species_richness": [0, 4],
            "mammal_record_count": [0, 15],
        }
    )

    frame = add_bird_observation_scores(frame)
    frame = add_mammal_observation_scores(frame)
    frame = add_biodiversity_observation_score(frame)

    assert frame.loc[0, "biodiversity_taxa_present"] == 1
    assert frame.loc[1, "biodiversity_taxa_present"] == 2
    assert frame.loc[1, "biodiversity_observation_score_raw"] > frame.loc[0, "biodiversity_observation_score_raw"]
    assert frame["biodiversity_record_coverage_score"].between(0, 100).all()


def test_restoration_opportunity_uses_percent_habitat_share() -> None:
    frame = pd.DataFrame(
        {
            "priority_habitat_share": [0.0, 80.0],
            "connectivity_score": [100.0, 100.0],
        }
    )

    result = add_restoration_opportunity_scores(frame)

    assert result.loc[0, "restoration_opportunity_score"] == 100.0
    assert result.loc[1, "restoration_opportunity_score"] == 20.0
