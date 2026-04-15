from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.build_grid import build_hex_grid
from src.features import (
    add_alc_opportunity_feature,
    add_distance_to_habitat_feature,
    add_habitat_share_feature,
    combine_feature_table,
    corine_habitat_proxy,
)
from src.ingest import (
    DataAsset,
    england_bbox_bng,
    england_bbox_corine,
    ensure_bng,
    repair_geometries,
    write_geoparquet,
)
from src.score import (
    add_boundary_penalty,
    add_connectivity_score,
    add_restoration_opportunity_scores,
    apply_scenarios,
)

ALC_CACHE_PATH = Path("data/interim/alc_clean.parquet")


def _load_corine_subset(asset: DataAsset) -> gpd.GeoDataFrame:
    local_subset = Path("data/interim/corine_subset.parquet")
    if local_subset.exists():
        return gpd.read_parquet(local_subset)
    return gpd.read_file(asset.path, layer=asset.layer, bbox=england_bbox_corine())


def _load_clean_alc(asset: DataAsset, *, verbose: bool = False) -> gpd.GeoDataFrame:
    """Load a cached cleaned ALC layer or build it once."""

    if ALC_CACHE_PATH.exists():
        if verbose:
            print(f"[pipeline] using cached ALC: {ALC_CACHE_PATH}", flush=True)
        return gpd.read_parquet(ALC_CACHE_PATH)

    if verbose:
        print("[pipeline] building cached ALC layer", flush=True)
    alc = repair_geometries(
        ensure_bng(gpd.read_file(asset.path)),
        allowed_geom_types=("Polygon", "MultiPolygon"),
    )
    alc.columns = alc.columns.str.lower()
    write_geoparquet(alc, ALC_CACHE_PATH)
    return alc


def _boundary_proxy(alc: gpd.GeoDataFrame, buffer_m: float = 2000) -> gpd.GeoDataFrame:
    """Build an approximate analysis boundary from available layers.

    This is a temporary fallback for local development only. Replace it with an
    official England boundary as soon as one is available.
    """

    cleaned_alc = repair_geometries(alc, allowed_geom_types=("Polygon", "MultiPolygon"))
    footprint = pd.DataFrame({"geometry": cleaned_alc.geometry})
    footprint = gpd.GeoDataFrame(footprint, geometry="geometry", crs=alc.crs)
    dissolved = footprint.union_all()
    proxy = gpd.GeoDataFrame(geometry=[dissolved.buffer(buffer_m)], crs=alc.crs)
    proxy = gpd.clip(proxy, england_bbox_bng())
    proxy = proxy.explode(ignore_index=True)
    proxy = proxy.loc[[proxy.geometry.area.idxmax()]].copy()
    proxy["boundary_type"] = "proxy_from_alc_and_corine"
    return proxy


def build_mvp_outputs(
    *,
    out_dir: Path = Path("data/interim/mvp"),
    boundary_path: Path | None = None,
    boundary_layer: str | None = None,
    cell_diameter_m: float = 1000,
    tile_size_m: float = 50_000,
    verbose: bool = False,
    reuse_existing: bool = True,
) -> dict[str, Path]:
    """Build a first-pass scored grid using the currently available layers."""

    out_dir.mkdir(parents=True, exist_ok=True)

    alc_asset = DataAsset(
        name="alc",
        path=Path("data/raw/alc/ALC_Grades_(Provisional)___ADAS_&_Defra.shp"),
        description="Provisional Agricultural Land Classification for England",
    )
    corine_asset = DataAsset(
        name="corine",
        path=Path("data/raw/corine/U2018_CLC2018_V2020_20u1.gpkg"),
        layer="U2018_CLC2018_V2020_20u1",
        description="CORINE land cover",
    )

    boundary_out = out_dir / "analysis_boundary.parquet"
    corine_out = out_dir / "corine_england_subset.parquet"
    habitat_out = out_dir / "habitat_proxy.parquet"
    grid_out = out_dir / "hex_grid.parquet"
    scores_out = out_dir / "hex_scores.parquet"
    grid_tiles_dir = out_dir / "grid_tiles"
    habitat_share_dir = out_dir / "feature_chunks" / "habitat_share"
    habitat_distance_dir = out_dir / "feature_chunks" / "distance"
    alc_feature_dir = out_dir / "feature_chunks" / "alc"

    if reuse_existing and scores_out.exists():
        if verbose:
            print(f"[pipeline] reusing existing scores: {scores_out}", flush=True)
        return {
            "boundary": boundary_out,
            "corine_subset": corine_out,
            "habitat_proxy": habitat_out,
            "grid": grid_out,
            "scores": scores_out,
        }

    if verbose:
        print("[pipeline] loading ALC", flush=True)
    alc = _load_clean_alc(alc_asset, verbose=verbose)

    if verbose:
        print("[pipeline] loading CORINE", flush=True)
    if reuse_existing and corine_out.exists():
        corine = gpd.read_parquet(corine_out)
    else:
        corine = _load_corine_subset(corine_asset)
        corine.columns = corine.columns.str.lower()
        write_geoparquet(corine, corine_out)
    corine.columns = corine.columns.str.lower()

    if reuse_existing and habitat_out.exists():
        habitat = gpd.read_parquet(habitat_out)
    else:
        habitat = corine_habitat_proxy(corine, code_column="code_18")
        write_geoparquet(habitat, habitat_out)

    if reuse_existing and boundary_out.exists():
        boundary = gpd.read_parquet(boundary_out)
    else:
        if boundary_path is not None:
            if verbose:
                print("[pipeline] loading official boundary", flush=True)
            if boundary_path.suffix == ".parquet":
                boundary = ensure_bng(gpd.read_parquet(boundary_path))
            else:
                boundary = ensure_bng(gpd.read_file(boundary_path, layer=boundary_layer))
            boundary["boundary_type"] = "official_input"
        else:
            boundary = _boundary_proxy(alc)
        write_geoparquet(boundary, boundary_out)

    if reuse_existing and grid_out.exists():
        if verbose:
            print(f"[pipeline] reusing existing grid: {grid_out}", flush=True)
        grid = gpd.read_parquet(grid_out)
    else:
        if verbose:
            print("[pipeline] building grid", flush=True)
        grid = build_hex_grid(
            boundary,
            cell_diameter_m=cell_diameter_m,
            tile_size_m=tile_size_m,
            verbose=verbose,
            checkpoint_dir=grid_tiles_dir,
        )
        write_geoparquet(grid, grid_out)

    if verbose:
        print("[pipeline] habitat share", flush=True)
    habitat_share = add_habitat_share_feature(
        grid,
        habitat,
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=habitat_share_dir,
    )
    if verbose:
        print("[pipeline] habitat distance", flush=True)
    habitat_distance = add_distance_to_habitat_feature(
        grid,
        habitat,
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=habitat_distance_dir,
    )
    if verbose:
        print("[pipeline] ALC feature", flush=True)
    alc_feature = add_alc_opportunity_feature(
        grid,
        alc,
        grade_column="alc_grade",
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=alc_feature_dir,
    )

    features = combine_feature_table(grid, habitat_share, habitat_distance, alc_feature)
    expected_full_hex_area_m2 = 3 * (3**0.5) / 2 * ((cell_diameter_m / 2) ** 2)
    features["cell_area_ratio"] = (
        features.geometry.area / expected_full_hex_area_m2
    ).clip(lower=0, upper=1)
    features = add_connectivity_score(features)
    features = add_restoration_opportunity_scores(features)
    features = add_boundary_penalty(features)

    # Placeholder scores until flood and peat layers are wired in.
    features["flood_opportunity_score_raw"] = 0.0
    features["peat_opportunity_score_raw"] = 0.0
    features["priority_habitat_share"] = features["priority_habitat_share"].fillna(0) * 100

    scored = apply_scenarios(features)

    write_geoparquet(
        gpd.GeoDataFrame(scored, geometry="geometry", crs=grid.crs),
        scores_out,
    )

    outputs = {
        "boundary": boundary_out,
        "corine_subset": corine_out,
        "habitat_proxy": habitat_out,
        "grid": grid_out,
        "scores": scores_out,
    }
    return outputs
