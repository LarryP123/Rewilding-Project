from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from src.features import (
    add_distance_to_habitat_feature,
    add_flood_opportunity_feature,
    add_habitat_share_feature,
    add_mammal_observation_feature,
    add_observation_feature,
    add_peat_opportunity_feature,
    add_weighted_area_feature,
)


def _square(min_x: float, min_y: float, max_x: float, max_y: float) -> Polygon:
    return Polygon(
        [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
        ]
    )


@pytest.fixture
def grid() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "hex_id": ["hex_a", "hex_b"],
            "geometry": [
                _square(0, 0, 10, 10),
                _square(20, 0, 30, 10),
            ],
        },
        crs="EPSG:27700",
    )


def test_add_habitat_share_feature_calculates_expected_intersection_share(
    grid: gpd.GeoDataFrame,
) -> None:
    habitat = gpd.GeoDataFrame(
        {
            "geometry": [
                _square(0, 0, 10, 10),
                _square(20, 0, 25, 10),
            ]
        },
        crs=grid.crs,
    )

    result = add_habitat_share_feature(grid, habitat, tile_size_m=1_000)
    actual = result.set_index("hex_id")["priority_habitat_share"]

    assert actual["hex_a"] == pytest.approx(1.0)
    assert actual["hex_b"] == pytest.approx(0.5)


def test_add_distance_to_habitat_feature_uses_nearest_geometry_per_cell(
    grid: gpd.GeoDataFrame,
) -> None:
    habitat = gpd.GeoDataFrame(
        {
            "geometry": [
                _square(4, 4, 6, 6),
                _square(32, 4, 34, 6),
            ]
        },
        crs=grid.crs,
    )

    result = add_distance_to_habitat_feature(grid, habitat, tile_size_m=1_000)
    actual = result.set_index("hex_id")["distance_to_priority_habitat_m"]

    assert actual["hex_a"] == pytest.approx(0.0)
    assert actual["hex_b"] == pytest.approx(7.0)


def test_add_weighted_area_feature_respects_polygon_weights(grid: gpd.GeoDataFrame) -> None:
    weighted = gpd.GeoDataFrame(
        {
            "opportunity_weight": [100.0, 50.0],
            "geometry": [
                _square(0, 0, 10, 10),
                _square(20, 0, 30, 10),
            ],
        },
        crs=grid.crs,
    )

    result = add_weighted_area_feature(grid, weighted, tile_size_m=1_000)
    actual = result.set_index("hex_id")["weighted_share"]

    assert actual["hex_a"] == pytest.approx(1.0)
    assert actual["hex_b"] == pytest.approx(0.5)


def test_add_observation_feature_aggregates_richness_and_record_count(grid: gpd.GeoDataFrame) -> None:
    observations = gpd.GeoDataFrame(
        {
            "species_guid": ["sp1", "sp1", "sp2", "sp3"],
            "geometry": [
                Point(1, 1),
                Point(2, 2),
                Point(4, 4),
                Point(24, 4),
            ],
        },
        crs=grid.crs,
    )

    result = add_observation_feature(grid, observations, tile_size_m=1_000).set_index("hex_id")

    assert result.loc["hex_a", "species_richness"] == pytest.approx(2.0)
    assert result.loc["hex_a", "record_count"] == pytest.approx(3.0)
    assert result.loc["hex_b", "species_richness"] == pytest.approx(1.0)
    assert result.loc["hex_b", "record_count"] == pytest.approx(1.0)


def test_add_mammal_observation_feature_uses_mammal_column_names(grid: gpd.GeoDataFrame) -> None:
    observations = gpd.GeoDataFrame(
        {
            "species_guid": ["bat", "fox"],
            "geometry": [
                Point(1, 1),
                Point(24, 4),
            ],
        },
        crs=grid.crs,
    )

    result = add_mammal_observation_feature(grid, observations, tile_size_m=1_000).set_index("hex_id")

    assert result.loc["hex_a", "mammal_species_richness"] == pytest.approx(1.0)
    assert result.loc["hex_a", "mammal_record_count"] == pytest.approx(1.0)
    assert result.loc["hex_b", "mammal_species_richness"] == pytest.approx(1.0)
    assert result.loc["hex_b", "mammal_record_count"] == pytest.approx(1.0)


def test_add_flood_opportunity_feature_prefers_dedicated_dataset_weights(grid: gpd.GeoDataFrame) -> None:
    flood = gpd.GeoDataFrame(
        {
            "flood_zone": ["Functional Floodplain", "Zone 2"],
            "geometry": [
                _square(0, 0, 10, 10),
                _square(20, 0, 25, 10),
            ],
        },
        crs=grid.crs,
    )

    result = add_flood_opportunity_feature(
        grid,
        flood,
        source_name="dedicated_dataset",
        tile_size_m=1_000,
    ).set_index("hex_id")

    assert result.loc["hex_a", "flood_feature_source"] == "dedicated_dataset"
    assert result.loc["hex_a", "flood_opportunity_score_raw"] > result.loc["hex_b", "flood_opportunity_score_raw"]


def test_add_peat_opportunity_feature_uses_dedicated_condition_weighting(grid: gpd.GeoDataFrame) -> None:
    peat = gpd.GeoDataFrame(
        {
            "condition": ["Near natural deep peat", "Modified shallow peat"],
            "geometry": [
                _square(0, 0, 10, 10),
                _square(20, 0, 25, 10),
            ],
        },
        crs=grid.crs,
    )

    result = add_peat_opportunity_feature(
        grid,
        peat,
        source_name="dedicated_dataset",
        tile_size_m=1_000,
    ).set_index("hex_id")

    assert result.loc["hex_a", "peat_feature_source"] == "dedicated_dataset"
    assert result.loc["hex_a", "peat_opportunity_score_raw"] > result.loc["hex_b", "peat_opportunity_score_raw"]
