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
CORINE_FLOOD_SHARE_CODES = frozenset({"411", "421", "423"})
CORINE_FLOOD_PROXIMITY_CODES = frozenset({"411", "421", "423", "511", "512", "521", "522", "523"})
CORINE_PEAT_CORE_CODES = frozenset({"412"})
CORINE_PEAT_CONTEXT_CODES = frozenset({"322", "324", "411", "412"})
FLOOD_SCORE_COLUMN_CANDIDATES = (
    "flood_score",
    "risk_score",
    "score",
    "suitability_score",
    "weight",
)
FLOOD_CLASS_COLUMN_CANDIDATES = (
    "zone",
    "flood_zone",
    "risk",
    "risk_band",
    "class",
    "class_name",
    "designation",
    "category",
)
PEAT_SCORE_COLUMN_CANDIDATES = (
    "peat_score",
    "condition_score",
    "restoration_score",
    "carbon_score",
    "score",
    "suitability_score",
    "weight",
)
PEAT_CLASS_COLUMN_CANDIDATES = (
    "peat_class",
    "peat_category",
    "peat_type",
    "condition",
    "condition_class",
    "class",
    "class_name",
    "category",
    "descriptive_group",
)


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


def corine_class_proxy(
    corine: gpd.GeoDataFrame,
    codes: set[str] | frozenset[str],
    *,
    code_column: str = "code_18",
    feature_column: str = "proxy",
) -> gpd.GeoDataFrame:
    """Filter CORINE polygons to an explicit set of class codes."""

    proxy = corine.loc[corine[code_column].astype(str).isin(codes)].copy()
    proxy[feature_column] = 1
    return gpd.GeoDataFrame(proxy, geometry="geometry", crs=corine.crs)


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

    if habitat.empty:
        result = base_grid.copy()
        result[feature_name] = np.nan
        return result

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


def _inverse_distance_score(distance: pd.Series) -> pd.Series:
    """Scale distances so nearer features score closer to 100."""

    non_null = distance.dropna()
    if non_null.empty:
        return pd.Series([0.0] * len(distance), index=distance.index, dtype="Float64")

    max_distance = non_null.max()
    if max_distance == 0:
        return pd.Series([100.0] * len(distance), index=distance.index, dtype="Float64")

    score = 100 - ((distance.fillna(max_distance) / max_distance) * 100)
    return score.clip(lower=0, upper=100).astype("Float64")


def _resolve_numeric_score_column(
    frame: gpd.GeoDataFrame,
    candidates: tuple[str, ...],
) -> pd.Series | None:
    for column in candidates:
        if column not in frame.columns:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.notna().any():
            max_value = numeric.dropna().max()
            if max_value <= 1:
                numeric = numeric * 100
            return numeric.clip(lower=0, upper=100)
    return None


def _resolve_text_class_column(
    frame: gpd.GeoDataFrame,
    candidates: tuple[str, ...],
) -> pd.Series | None:
    for column in candidates:
        if column in frame.columns:
            return frame[column].astype(str).str.lower()
    return None


def _derive_flood_weight(source: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    weighted = source.copy()
    numeric = _resolve_numeric_score_column(weighted, FLOOD_SCORE_COLUMN_CANDIDATES)
    if numeric is not None:
        weighted["opportunity_weight"] = numeric.round(2)
        return weighted

    text = _resolve_text_class_column(weighted, FLOOD_CLASS_COLUMN_CANDIDATES)
    if text is None:
        weighted["opportunity_weight"] = 100.0
        return weighted

    weights = pd.Series(40.0, index=weighted.index, dtype="Float64")
    weights = weights.mask(text.str.contains("3b|functional", na=False), 100.0)
    weights = weights.mask(text.str.contains(r"\bzone 3\b|\bzone3\b|high", na=False), 90.0)
    weights = weights.mask(text.str.contains(r"\bzone 2\b|\bzone2\b|medium", na=False), 65.0)
    weights = weights.mask(text.str.contains(r"\bzone 1\b|\bzone1\b|low", na=False), 30.0)
    weighted["opportunity_weight"] = weights.round(2)
    return weighted


def _derive_peat_weight(source: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    weighted = source.copy()
    numeric = _resolve_numeric_score_column(weighted, PEAT_SCORE_COLUMN_CANDIDATES)
    if numeric is not None:
        weighted["opportunity_weight"] = numeric.round(2)
        return weighted

    text = _resolve_text_class_column(weighted, PEAT_CLASS_COLUMN_CANDIDATES)
    if text is None:
        weighted["opportunity_weight"] = 100.0
        return weighted

    weights = pd.Series(50.0, index=weighted.index, dtype="Float64")
    weights = weights.mask(text.str.contains("deep peat|peat bog|raised bog|blanket bog", na=False), 100.0)
    weights = weights.mask(text.str.contains("near natural|restorable|rewettable", na=False), 85.0)
    weights = weights.mask(text.str.contains("shallow peat|modified", na=False), 60.0)
    weights = weights.mask(text.str.contains("drained|wasted|degraded", na=False), 70.0)
    weights = weights.mask(text.str.contains("mineral", na=False), 0.0)
    weighted["opportunity_weight"] = weights.round(2)
    return weighted


def add_weighted_area_feature(
    grid: gpd.GeoDataFrame,
    source: gpd.GeoDataFrame,
    *,
    weight_column: str = "opportunity_weight",
    share_feature_name: str = "weighted_share",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Compute per-hex weighted area share from polygons with 0-100 weights."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(source.crs) if grid.crs != source.crs else grid.copy()
    source = source.copy()

    chunks: list[pd.DataFrame] = []
    for index, chunk in iter_grid_chunks(working_grid[["hex_id", "geometry"]], tile_size_m=tile_size_m):
        if checkpoint_dir is not None:
            checkpoint = _checkpoint_file(checkpoint_dir, "weighted_share", index)
            if checkpoint.exists():
                chunks.append(pd.read_parquet(checkpoint))
                if verbose:
                    print(f"[weighted_share] chunk {index}: reuse", flush=True)
                continue

        chunk = chunk.copy()
        chunk["hex_area_m2"] = chunk.geometry.area
        subset = _source_subset(source[[weight_column, "geometry"]], chunk.total_bounds)
        if subset.empty:
            chunk[share_feature_name] = 0.0
            result = chunk[["hex_id", share_feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        intersections = gpd.overlay(chunk[["hex_id", "geometry"]], subset, how="intersection")
        if intersections.empty:
            chunk[share_feature_name] = 0.0
            result = chunk[["hex_id", share_feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        intersections["weighted_intersection_area_m2"] = (
            intersections.geometry.area * intersections[weight_column].fillna(0).clip(lower=0, upper=100) / 100
        )
        weighted_area = (
            intersections.groupby("hex_id", as_index=False)["weighted_intersection_area_m2"].sum()
        )
        merged = chunk.merge(weighted_area, on="hex_id", how="left")
        merged["weighted_intersection_area_m2"] = merged["weighted_intersection_area_m2"].fillna(0)
        merged[share_feature_name] = merged["weighted_intersection_area_m2"] / merged["hex_area_m2"]
        result = merged[["hex_id", share_feature_name]]
        if checkpoint_dir is not None:
            result.to_parquet(checkpoint)
        chunks.append(result)
        if verbose:
            print(f"[weighted_share] chunk {index}: {len(chunk)} cells", flush=True)

    result = base_grid.merge(pd.concat(chunks, ignore_index=True), on="hex_id", how="left")
    result[share_feature_name] = result[share_feature_name].fillna(0.0)
    return result


def add_flood_opportunity_feature(
    grid: gpd.GeoDataFrame,
    source: gpd.GeoDataFrame,
    *,
    code_column: str = "code_18",
    feature_name: str = "flood_opportunity_score_raw",
    source_name: str = "corine_proxy",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Build a flood opportunity score from dedicated polygons or a CORINE fallback."""

    if source_name == "corine_proxy":
        flood_footprint = corine_class_proxy(
            source,
            CORINE_FLOOD_SHARE_CODES,
            code_column=code_column,
            feature_column="flood_share_proxy",
        )
        flood_proximity_source = corine_class_proxy(
            source,
            CORINE_FLOOD_PROXIMITY_CODES,
            code_column=code_column,
            feature_column="flood_distance_proxy",
        )
        flood_share = add_habitat_share_feature(
            grid,
            flood_footprint,
            feature_name="floodplain_wetland_share",
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=checkpoint_dir / "share" if checkpoint_dir is not None else None,
        )
        flood_weighted_share = flood_share.rename(
            columns={"floodplain_wetland_share": "flood_weighted_share"}
        )
    else:
        weighted_source = _derive_flood_weight(source)
        flood_share = add_habitat_share_feature(
            grid,
            weighted_source[["geometry"]],
            feature_name="flood_extent_share",
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=checkpoint_dir / "extent_share" if checkpoint_dir is not None else None,
        )
        flood_weighted_share = add_weighted_area_feature(
            grid,
            weighted_source[["geometry", "opportunity_weight"]],
            weight_column="opportunity_weight",
            share_feature_name="flood_weighted_share",
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=checkpoint_dir / "weighted_share" if checkpoint_dir is not None else None,
        )
        flood_footprint = weighted_source
        flood_proximity_source = weighted_source

    flood_distance = add_distance_to_habitat_feature(
        grid,
        flood_proximity_source,
        feature_name="distance_to_flood_m",
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=checkpoint_dir / "distance" if checkpoint_dir is not None else None,
    )

    flood = combine_feature_table(grid, flood_share, flood_weighted_share, flood_distance)
    if "flood_extent_share" not in flood.columns:
        flood["flood_extent_share"] = flood.get("floodplain_wetland_share", 0.0)
    flood["flood_extent_share"] = flood["flood_extent_share"].fillna(0.0).clip(lower=0, upper=1)
    flood["flood_weighted_share"] = flood["flood_weighted_share"].fillna(0.0).clip(lower=0, upper=1)
    flood["flood_proximity_score"] = _inverse_distance_score(flood["distance_to_flood_m"])
    area_weight = 0.7 if source_name != "corine_proxy" else 0.6
    distance_weight = 0.3 if source_name != "corine_proxy" else 0.4
    flood[feature_name] = (
        (flood["flood_weighted_share"] * 100 * area_weight) + (flood["flood_proximity_score"] * distance_weight)
    ).round(2)
    flood["flood_feature_source"] = source_name
    return flood


def add_peat_opportunity_feature(
    grid: gpd.GeoDataFrame,
    source: gpd.GeoDataFrame,
    *,
    code_column: str = "code_18",
    feature_name: str = "peat_opportunity_score_raw",
    source_name: str = "corine_proxy",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Build a peat opportunity score from dedicated polygons or a CORINE fallback."""

    if source_name == "corine_proxy":
        peat_core = corine_class_proxy(
            source,
            CORINE_PEAT_CORE_CODES,
            code_column=code_column,
            feature_column="peat_core_proxy",
        )
        peat_context = corine_class_proxy(
            source,
            CORINE_PEAT_CONTEXT_CODES,
            code_column=code_column,
            feature_column="peat_context_proxy",
        )
        peat_share = add_habitat_share_feature(
            grid,
            peat_core,
            feature_name="peat_bog_share",
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=checkpoint_dir / "core_share" if checkpoint_dir is not None else None,
        )
        peat_context_share = add_habitat_share_feature(
            grid,
            peat_context,
            feature_name="peatland_context_share",
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=checkpoint_dir / "context_share" if checkpoint_dir is not None else None,
        )
        peat_weighted_share = peat_share.rename(columns={"peat_bog_share": "peat_weighted_share"})
        peat_distance_source = peat_core
    else:
        weighted_source = _derive_peat_weight(source)
        peat_share = add_habitat_share_feature(
            grid,
            weighted_source[["geometry"]],
            feature_name="peat_extent_share",
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=checkpoint_dir / "extent_share" if checkpoint_dir is not None else None,
        )
        peat_context_share = peat_share.rename(columns={"peat_extent_share": "peatland_context_share"})
        peat_weighted_share = add_weighted_area_feature(
            grid,
            weighted_source[["geometry", "opportunity_weight"]],
            weight_column="opportunity_weight",
            share_feature_name="peat_weighted_share",
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=checkpoint_dir / "weighted_share" if checkpoint_dir is not None else None,
        )
        peat_distance_source = weighted_source

    peat_distance = add_distance_to_habitat_feature(
        grid,
        peat_distance_source,
        feature_name="distance_to_peat_m",
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=checkpoint_dir / "distance" if checkpoint_dir is not None else None,
    )

    peat = combine_feature_table(grid, peat_share, peat_context_share, peat_weighted_share, peat_distance)
    if "peat_extent_share" not in peat.columns:
        peat["peat_extent_share"] = peat.get("peat_bog_share", 0.0)
    peat["peat_extent_share"] = peat["peat_extent_share"].fillna(0.0).clip(lower=0, upper=1)
    peat["peatland_context_share"] = peat["peatland_context_share"].fillna(0.0).clip(lower=0, upper=1)
    peat["peat_weighted_share"] = peat["peat_weighted_share"].fillna(0.0).clip(lower=0, upper=1)
    peat["peat_proximity_score"] = _inverse_distance_score(peat["distance_to_peat_m"])
    if source_name == "corine_proxy":
        peat[feature_name] = (
            (peat["peat_weighted_share"] * 100 * 0.5)
            + (peat["peatland_context_share"] * 100 * 0.2)
            + (peat["peat_proximity_score"] * 0.3)
        ).round(2)
    else:
        peat[feature_name] = (
            (peat["peat_weighted_share"] * 100 * 0.7)
            + (peat["peat_proximity_score"] * 0.3)
        ).round(2)
    peat["peat_feature_source"] = source_name
    return peat


def add_observation_feature(
    grid: gpd.GeoDataFrame,
    observations: gpd.GeoDataFrame,
    *,
    species_column: str = "species_guid",
    richness_feature_name: str = "species_richness",
    record_count_feature_name: str = "record_count",
    checkpoint_prefix: str = "observations",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Aggregate species observations into per-hex richness and record counts."""

    base_grid = grid.copy()
    working_grid = grid.to_crs(observations.crs) if grid.crs != observations.crs else grid.copy()
    observations = observations.copy()

    if observations.empty:
        result = base_grid.copy()
        result[richness_feature_name] = 0.0
        result[record_count_feature_name] = 0.0
        return result

    chunks: list[pd.DataFrame] = []
    for index, chunk in iter_grid_chunks(working_grid[["hex_id", "geometry"]], tile_size_m=tile_size_m):
        if checkpoint_dir is not None:
            checkpoint = _checkpoint_file(checkpoint_dir, checkpoint_prefix, index)
            if checkpoint.exists():
                chunks.append(pd.read_parquet(checkpoint))
                if verbose:
                    print(f"[{checkpoint_prefix}] chunk {index}: reuse", flush=True)
                continue

        chunk = chunk.copy()
        subset = _source_subset(observations[[species_column, "geometry"]], chunk.total_bounds)
        if subset.empty:
            chunk[richness_feature_name] = 0.0
            chunk[record_count_feature_name] = 0.0
            result = chunk[["hex_id", richness_feature_name, record_count_feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        joined = gpd.sjoin(
            chunk[["hex_id", "geometry"]],
            subset[[species_column, "geometry"]],
            how="left",
            predicate="intersects",
        )
        observed = joined.dropna(subset=[species_column]).copy()
        if observed.empty:
            chunk[richness_feature_name] = 0.0
            chunk[record_count_feature_name] = 0.0
            result = chunk[["hex_id", richness_feature_name, record_count_feature_name]]
            if checkpoint_dir is not None:
                result.to_parquet(checkpoint)
            chunks.append(result)
            continue

        richness = observed.groupby("hex_id", as_index=False)[species_column].nunique().rename(
            columns={species_column: richness_feature_name}
        )
        record_count = observed.groupby("hex_id", as_index=False).size().rename(
            columns={"size": record_count_feature_name}
        )
        result = (
            chunk[["hex_id"]]
            .merge(richness, on="hex_id", how="left")
            .merge(record_count, on="hex_id", how="left")
        )
        result[richness_feature_name] = result[richness_feature_name].fillna(0.0)
        result[record_count_feature_name] = result[record_count_feature_name].fillna(0.0)
        if checkpoint_dir is not None:
            result.to_parquet(checkpoint)
        chunks.append(result)
        if verbose:
            print(f"[{checkpoint_prefix}] chunk {index}: {len(chunk)} cells", flush=True)

    result = base_grid.merge(pd.concat(chunks, ignore_index=True), on="hex_id", how="left")
    result[richness_feature_name] = result[richness_feature_name].fillna(0.0)
    result[record_count_feature_name] = result[record_count_feature_name].fillna(0.0)
    return result


def add_bird_observation_feature(
    grid: gpd.GeoDataFrame,
    observations: gpd.GeoDataFrame,
    *,
    species_column: str = "species_guid",
    richness_feature_name: str = "bird_species_richness",
    record_count_feature_name: str = "bird_record_count",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Aggregate bird observations into per-hex richness and record counts."""

    return add_observation_feature(
        grid,
        observations,
        species_column=species_column,
        richness_feature_name=richness_feature_name,
        record_count_feature_name=record_count_feature_name,
        checkpoint_prefix="bird_observations",
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=checkpoint_dir,
    )


def add_mammal_observation_feature(
    grid: gpd.GeoDataFrame,
    observations: gpd.GeoDataFrame,
    *,
    species_column: str = "species_guid",
    richness_feature_name: str = "mammal_species_richness",
    record_count_feature_name: str = "mammal_record_count",
    tile_size_m: float = 50_000,
    verbose: bool = False,
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Aggregate mammal observations into per-hex richness and record counts."""

    return add_observation_feature(
        grid,
        observations,
        species_column=species_column,
        richness_feature_name=richness_feature_name,
        record_count_feature_name=record_count_feature_name,
        checkpoint_prefix="mammal_observations",
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=checkpoint_dir,
    )


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
