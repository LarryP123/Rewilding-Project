from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from src.geography import attach_geography_name, dominant_name_by_group, infer_name_column


def _square(min_x: float, min_y: float, max_x: float, max_y: float) -> Polygon:
    return Polygon(
        [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
        ]
    )


def test_infer_name_column_prefers_lnrs_style_names() -> None:
    columns = ["OBJECTID", "LNRS_NAME", "geometry"]
    assert infer_name_column(columns) == "LNRS_NAME"


def test_attach_geography_name_joins_representative_points(tmp_path: Path) -> None:
    frame = gpd.GeoDataFrame(
        {
            "hex_id": ["hex_a", "hex_b"],
            "geometry": [_square(0, 0, 10, 10), _square(20, 0, 30, 10)],
        },
        crs="EPSG:27700",
    )
    geography = gpd.GeoDataFrame(
        {
            "LNRS_NAME": ["North Strategy", "South Strategy"],
            "geometry": [_square(-5, -5, 15, 15), _square(15, -5, 35, 15)],
        },
        crs=frame.crs,
    )
    path = tmp_path / "lnrs.geojson"
    geography.to_file(path, driver="GeoJSON")

    enriched = attach_geography_name(frame, path, join_key="hex_id", output_column="lnrs_name")

    actual = enriched.set_index("hex_id")["lnrs_name"].to_dict()
    assert actual == {"hex_a": "North Strategy", "hex_b": "South Strategy"}


def test_dominant_name_by_group_prefers_most_common_then_strongest_score() -> None:
    frame = pd.DataFrame(
        {
            "hex_id": ["a", "b", "c", "d"],
            "cluster_id": ["cluster_1", "cluster_1", "cluster_1", "cluster_2"],
            "lnrs_name": ["Strategy A", "Strategy A", "Strategy B", "Strategy C"],
            "scenario_balanced": [70.0, 68.0, 90.0, 75.0],
        }
    )

    summary = dominant_name_by_group(
        frame,
        group_column="cluster_id",
        name_column="lnrs_name",
        score_column="scenario_balanced",
        primary_output_column="primary_lnrs_name",
        list_output_column="lnrs_names",
        count_output_column="lnrs_count",
    ).set_index("cluster_id")

    assert summary.loc["cluster_1", "primary_lnrs_name"] == "Strategy A"
    assert summary.loc["cluster_1", "lnrs_names"] == "Strategy A | Strategy B"
    assert summary.loc["cluster_1", "lnrs_count"] == 2
    assert summary.loc["cluster_2", "primary_lnrs_name"] == "Strategy C"
