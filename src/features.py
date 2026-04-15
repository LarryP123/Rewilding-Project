from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

ALC_OPPORTUNITY_MAP = {
    1: 0,
    2: 20,
    3: 50,
    4: 80,
    5: 100,
}

CORINE_HABITAT_PREFIXES = ("3", "4")


def iter_grid_chunks(
    grid: gpd.GeoDataFrame,
    tile_size_m: float = 50_000,
) -> list[tuple[int, gpd.GeoDataFrame]]:
    """Split a grid into deterministic spatial chunks using centroid tiles."""

    working = grid.copy()
    centroids = working.geometry.centroid
    working["_tile_x"] = ((centroids.x // tile_size_m).astype(int)).astype("int64")
    working["_tile_y"] = ((centroids.y // tile_size_m).astype(int)).astype("int64")
    return [
        (index, chunk.drop(columns=["_tile_x", "_tile_y"]))
        for index, (_, chunk) in enumerate(working.groupby(["_tile_x", "_tile_y"], sort=True), start=1)
    ]


def _source_subset(source: gpd.GeoDataFrame, bounds: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Clip a source frame to the bbox of a chunk using its spatial index."""

    if source.empty:
        return source.copy()
    hits = list(source.sindex.intersection(bounds))
    if not hits:
        return source.iloc[0:0].copy()
    subset = source.iloc[hits].copy()
    clip_box = box(*bounds)
    return subset[subset.geometry.intersects(clip_box)].copy()


def _checkpoint_file(checkpoint_dir: Path, prefix: str, chunk_index: int) -> Path:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir / f"{prefix}_{chunk_index:05d}.parquet"


def add_habitat_share_feature(
    grid: gpd.GeoDataFrame,
    habitat: gpd.GeoDataFrame,
    feature_name: str = "priority_habitat_share",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Compute the proportion of each hex covered by habitat polygons."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(habitat.crs) if grid.crs != habitat.crs else grid.copy()
    habitat = habitat.copy()

    chunks: list[pd.DataFrame] = []
    for index, chunk in iter_grid_chunks(working_grid[["hex_id", "geometry"]], tile_size_m=tile_size_m):
        if checkpoint_dir is not None:
            checkpoint = _checkpoint_file(checkpoint_dir, "habitat_share", index)
            if checkpoint.exists():
                chunks.append(pd.read_parquet(checkpoint))
                if verbose:
                    print(f"[habitat_share] chunk {index}: reuse", flush=True)
                continue

        chunk = chunk.copy()
        chunk["hex_area_m2"] = chunk.geometry.area
        subset = _source_subset(habitat[["geometry"]], chunk.total_bounds)
        if subset.empty:
            chunk[feature_name] = 0.0
            result = chunk[["hex_id", feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        intersections = gpd.overlay(chunk[["hex_id", "geometry"]], subset, how="intersection")
        if intersections.empty:
            chunk[feature_name] = 0.0
            result = chunk[["hex_id", feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        coverage = (
            intersections.assign(intersection_area_m2=intersections.geometry.area)
            .groupby("hex_id", as_index=False)["intersection_area_m2"]
            .sum()
        )
        merged = chunk.merge(coverage, on="hex_id", how="left")
        merged["intersection_area_m2"] = merged["intersection_area_m2"].fillna(0)
        merged[feature_name] = merged["intersection_area_m2"] / merged["hex_area_m2"]
        result = merged[["hex_id", feature_name]]
        if checkpoint_dir is not None:
            result.to_parquet(checkpoint)
        chunks.append(result)
        if verbose:
            print(f"[habitat_share] chunk {index}: {len(chunk)} cells", flush=True)

    result = base_grid.merge(pd.concat(chunks, ignore_index=True), on="hex_id", how="left")
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
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Compute nearest distance from hex centroids to habitat polygons."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(habitat.crs) if grid.crs != habitat.crs else grid.copy()
    habitat = habitat.copy()

    chunks: list[pd.DataFrame] = []
    for index, chunk in iter_grid_chunks(working_grid[["hex_id", "geometry"]], tile_size_m=tile_size_m):
        if checkpoint_dir is not None:
            checkpoint = _checkpoint_file(checkpoint_dir, "distance", index)
            if checkpoint.exists():
                chunks.append(pd.read_parquet(checkpoint))
                if verbose:
                    print(f"[distance] chunk {index}: reuse", flush=True)
                continue

        centroids = chunk.copy()
        centroids["geometry"] = centroids.geometry.centroid
        joined = gpd.sjoin_nearest(
            centroids[["hex_id", "geometry"]],
            habitat[["geometry"]],
            how="left",
            distance_col=feature_name,
        )
        result = joined[["hex_id", feature_name]]
        if checkpoint_dir is not None:
            result.to_parquet(checkpoint)
        chunks.append(result)
        if verbose:
            print(f"[distance] chunk {index}: {len(chunk)} cells", flush=True)

    return base_grid.merge(pd.concat(chunks, ignore_index=True), on="hex_id", how="left")


def add_alc_opportunity_feature(
    grid: gpd.GeoDataFrame,
    alc: gpd.GeoDataFrame,
    grade_column: str = "alc_grade",
    feature_name: str = "agri_opportunity_score_raw",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Assign an agriculture opportunity score from dominant ALC grade per hex."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(alc.crs) if grid.crs != alc.crs else grid.copy()
    alc = alc.copy()

    chunks: list[pd.DataFrame] = []
    for index, chunk in iter_grid_chunks(working_grid[["hex_id", "geometry"]], tile_size_m=tile_size_m):
        if checkpoint_dir is not None:
            checkpoint = _checkpoint_file(checkpoint_dir, "alc", index)
            if checkpoint.exists():
                chunks.append(pd.read_parquet(checkpoint))
                if verbose:
                    print(f"[alc] chunk {index}: reuse", flush=True)
                continue

        subset = _source_subset(alc[[grade_column, "geometry"]], chunk.total_bounds)
        if subset.empty:
            chunk[feature_name] = np.nan
            result = chunk[["hex_id", feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        intersections = gpd.overlay(
            chunk[["hex_id", "geometry"]],
            subset,
            how="intersection",
        )
        if intersections.empty:
            chunk[feature_name] = np.nan
            result = chunk[["hex_id", feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        intersections["intersection_area_m2"] = intersections.geometry.area
        dominant = (
            intersections.sort_values(["hex_id", "intersection_area_m2"], ascending=[True, False])
            .drop_duplicates("hex_id")
            .copy()
        )
        dominant[feature_name] = dominant[grade_column].apply(_normalize_alc_grade).map(ALC_OPPORTUNITY_MAP)
        result = dominant[["hex_id", feature_name]]
        if checkpoint_dir is not None:
            result.to_parquet(checkpoint)
        chunks.append(result)
        if verbose:
            print(f"[alc] chunk {index}: {len(chunk)} cells", flush=True)

    return base_grid.merge(pd.concat(chunks, ignore_index=True), on="hex_id", how="left")


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
