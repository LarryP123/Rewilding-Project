from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

ALC_OPPORTUNITY_MAP = {
    1: 0,
    2: 20,
    3: 50,
    4: 80,
    5: 100,
}

CORINE_HABITAT_PREFIXES = ("3", "4")


def add_habitat_share_feature(
    grid: gpd.GeoDataFrame,
    habitat: gpd.GeoDataFrame,
    feature_name: str = "priority_habitat_share",
) -> gpd.GeoDataFrame:
    """Compute the proportion of each hex covered by habitat polygons."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(habitat.crs) if grid.crs != habitat.crs else grid.copy()
    working_grid["hex_area_m2"] = working_grid.geometry.area

    intersections = gpd.overlay(
        working_grid[["hex_id", "geometry"]],
        habitat[["geometry"]],
        how="intersection",
    )
    if intersections.empty:
        base_grid[feature_name] = 0.0
        return base_grid

    coverage = (
        intersections.assign(intersection_area_m2=intersections.geometry.area)
        .groupby("hex_id", as_index=False)["intersection_area_m2"]
        .sum()
    )

    merged = working_grid.merge(coverage, on="hex_id", how="left")
    merged["intersection_area_m2"] = merged["intersection_area_m2"].fillna(0)
    merged[feature_name] = merged["intersection_area_m2"] / merged["hex_area_m2"]
    result = base_grid.merge(merged[["hex_id", feature_name]], on="hex_id", how="left")
    result[feature_name] = result[feature_name].fillna(0.0)
    return result


def corine_habitat_proxy(
    corine: gpd.GeoDataFrame,
    code_column: str = "code_18",
) -> gpd.GeoDataFrame:
    """Filter CORINE polygons to a simple natural-habitat proxy."""

    corine = corine.copy()
    codes = corine[code_column].astype(str)
    mask = codes.str.startswith(CORINE_HABITAT_PREFIXES)
    habitat = corine.loc[mask].copy()
    habitat["habitat_proxy"] = 1
    return gpd.GeoDataFrame(habitat, geometry="geometry", crs=corine.crs)


def add_distance_to_habitat_feature(
    grid: gpd.GeoDataFrame,
    habitat: gpd.GeoDataFrame,
    feature_name: str = "distance_to_priority_habitat_m",
) -> gpd.GeoDataFrame:
    """Compute nearest distance from hex centroids to habitat polygons."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(habitat.crs) if grid.crs != habitat.crs else grid.copy()

    centroids = working_grid.copy()
    centroids["geometry"] = centroids.geometry.centroid
    joined = gpd.sjoin_nearest(
        centroids[["hex_id", "geometry"]],
        habitat[["geometry"]],
        how="left",
        distance_col=feature_name,
    )
    return base_grid.merge(joined[["hex_id", feature_name]], on="hex_id", how="left")


def add_alc_opportunity_feature(
    grid: gpd.GeoDataFrame,
    alc: gpd.GeoDataFrame,
    grade_column: str = "alc_grade",
    feature_name: str = "agri_opportunity_score_raw",
) -> gpd.GeoDataFrame:
    """Assign an agriculture opportunity score from dominant ALC grade per hex."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(alc.crs) if grid.crs != alc.crs else grid.copy()

    intersections = gpd.overlay(
        working_grid[["hex_id", "geometry"]],
        alc[[grade_column, "geometry"]],
        how="intersection",
    )
    if intersections.empty:
        base_grid[feature_name] = np.nan
        return base_grid

    intersections["intersection_area_m2"] = intersections.geometry.area
    dominant = (
        intersections.sort_values(["hex_id", "intersection_area_m2"], ascending=[True, False])
        .drop_duplicates("hex_id")
        .copy()
    )

    dominant[feature_name] = dominant[grade_column].apply(_normalize_alc_grade).map(ALC_OPPORTUNITY_MAP)
    return base_grid.merge(dominant[["hex_id", feature_name]], on="hex_id", how="left")


def _normalize_alc_grade(value: object) -> int | None:
    """Convert common ALC labels like 'Grade 3' to integers."""

    if value is None or pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text.startswith("grade "):
        suffix = text.replace("grade ", "", 1).strip()
        return int(suffix) if suffix.isdigit() else None
    return int(text) if text.isdigit() else None


def combine_feature_table(*frames: gpd.GeoDataFrame | pd.DataFrame) -> pd.DataFrame:
    """Merge feature tables on hex_id without duplicating geometry columns."""

    if not frames:
        raise ValueError("At least one frame is required.")

    merged = frames[0].copy()
    for frame in frames[1:]:
        cols = [c for c in frame.columns if c == "hex_id" or c not in merged.columns]
        merged = merged.merge(frame[cols], on="hex_id", how="left")
    return merged
