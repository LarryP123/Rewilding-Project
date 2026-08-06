from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from src.features import (
    add_bng_opportunity_score,
    add_distance_to_habitat_feature,
    add_flood_opportunity_feature,
    add_habitat_share_feature,
    add_mammal_observation_feature,
    add_observation_feature,
    add_peat_opportunity_feature,
    add_rewilding_network_proximity_score,
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


def test_add_distance_to_habitat_feature_deduplicates_tied_nearest_matches(
    grid: gpd.GeoDataFrame,
) -> None:
    # hex_a's centroid is (5, 5). Both squares sit exactly 10m away, on
    # opposite sides, so sjoin_nearest returns two tied matches for hex_a.
    habitat = gpd.GeoDataFrame(
        {
            "geometry": [
                _square(15, 4, 16, 6),
                _square(-6, 4, -5, 6),
            ]
        },
        crs=grid.crs,
    )

    result = add_distance_to_habitat_feature(grid, habitat, tile_size_m=1_000)

    assert len(result) == len(grid)
    actual = result.set_index("hex_id")["distance_to_priority_habitat_m"]
    assert actual["hex_a"] == pytest.approx(10.0)


def test_add_bng_opportunity_score_favors_hexes_near_registered_sites(
    grid: gpd.GeoDataFrame,
) -> None:
    bng_sites = gpd.GeoDataFrame(
        {"geometry": [Point(5, 5)]},
        crs=grid.crs,
    )

    result = add_bng_opportunity_score(grid, bng_sites, tile_size_m=1_000)
    actual = result.set_index("hex_id")

    assert actual.loc["hex_a", "distance_to_bng_site_m"] == pytest.approx(0.0)
    assert actual.loc["hex_a", "bng_opportunity_score_raw"] == pytest.approx(100.0)
    assert actual.loc["hex_b", "bng_opportunity_score_raw"] < actual.loc["hex_a", "bng_opportunity_score_raw"]


def test_add_bng_opportunity_score_reprojects_mismatched_crs(
    grid: gpd.GeoDataFrame,
) -> None:
    bng_sites_native_crs = gpd.GeoDataFrame(
        {"geometry": [Point(5, 5)]},
        crs=grid.crs,
    )
    # EPSG:4277 (OSGB36 geographic) shares the same datum as EPSG:27700
    # (OSGB36 / British National Grid) — converting between them is a pure
    # map projection, not a datum shift, so it needs no external grid data
    # and is portable to sandboxes without full PROJ grid resources. Using
    # EPSG:4326 (WGS84) here instead would require a real OSGB36<->WGS84
    # datum transform, which depends on PROJ grid data that may not be
    # available everywhere and can silently degrade to NaN/inf if missing.
    bng_sites_other_crs = bng_sites_native_crs.to_crs(4277)
    assert bng_sites_other_crs.crs != grid.crs

    expected = add_bng_opportunity_score(grid, bng_sites_native_crs, tile_size_m=1_000)
    actual = add_bng_opportunity_score(grid, bng_sites_other_crs, tile_size_m=1_000)

    expected_distances = expected.set_index("hex_id")["distance_to_bng_site_m"]
    actual_distances = actual.set_index("hex_id")["distance_to_bng_site_m"]

    # This round-trip is a pure projection, not a datum shift, so it should
    # be accurate to well under a metre; the regression this guards against
    # (computing distance in degrees instead of metres) would be off by many
    # orders of magnitude more than this.
    for hex_id in expected_distances.index:
        assert actual_distances[hex_id] == pytest.approx(expected_distances[hex_id], abs=1.0)


def test_add_rewilding_network_proximity_score_favors_hexes_near_real_projects(
    grid: gpd.GeoDataFrame,
) -> None:
    projects = gpd.GeoDataFrame(
        {"geometry": [Point(5, 5)]},
        crs=grid.crs,
    )

    result = add_rewilding_network_proximity_score(grid, projects, tile_size_m=1_000)
    actual = result.set_index("hex_id")

    assert actual.loc["hex_a", "distance_to_rewilding_project_m"] == pytest.approx(0.0)
    assert actual.loc["hex_a", "rewilding_network_proximity_score_raw"] == pytest.approx(100.0)
    assert (
        actual.loc["hex_b", "rewilding_network_proximity_score_raw"]
        < actual.loc["hex_a", "rewilding_network_proximity_score_raw"]
    )


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
