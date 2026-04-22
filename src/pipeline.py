from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pyogrio

from src.canonical import (
    CANONICAL_FLOOD_PATH,
    CANONICAL_PEAT_PATH,
    CANONICAL_RUN_METADATA_PATH,
    canonical_source_contract,
)
from src.build_grid import build_hex_grid
from src.features import (
    add_alc_opportunity_feature,
    add_mammal_observation_feature,
    add_bird_observation_feature,
    add_distance_to_habitat_feature,
    add_flood_opportunity_feature,
    add_habitat_share_feature,
    add_peat_opportunity_feature,
    combine_feature_table,
    corine_habitat_proxy,
)
from src.ingest import (
    DataAsset,
    download_nbn_bird_observations,
    download_nbn_mammal_observations,
    england_bbox_bng,
    england_bbox_corine,
    ensure_bng,
    repair_geometries,
    write_geoparquet,
    write_json,
)
from src.score import (
    add_biodiversity_observation_score,
    add_bird_observation_scores,
    add_boundary_penalty,
    add_connectivity_score,
    add_mammal_observation_scores,
    add_restoration_opportunity_scores,
    apply_scenarios,
)

ALC_CACHE_PATH = Path("data/interim/alc_clean.parquet")
BIRD_OBSERVATION_CACHE_PATH = Path("data/interim/bird_observations_irecord_verified_2015plus_england.parquet")
MAMMAL_OBSERVATION_CACHE_PATH = Path("data/interim/mammal_observations_irecord_verified_2015plus_england.parquet")
DEFAULT_FLOOD_PATH_CANDIDATES = (
    Path("data/raw/flood/ea_flood_zones.parquet"),
    Path("data/raw/flood/ea_flood_zones.gpkg"),
    Path("data/raw/flood/ea_flood_zones.shp"),
)
DEFAULT_PEAT_PATH_CANDIDATES = (
    Path("data/raw/peat/england_peat_map.parquet"),
    Path("data/raw/peat/england_peat_map.gpkg"),
    Path("data/raw/peat/england_peat_map.shp"),
)
RUN_METADATA_FILENAME = "run_metadata.json"


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


def _existing_path(path: Path | None, candidates: tuple[Path, ...]) -> Path | None:
    if path is not None:
        return path if path.exists() else None
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_clean_vector_asset(
    asset: DataAsset,
    *,
    cache_path: Path,
    verbose: bool = False,
) -> gpd.GeoDataFrame:
    """Load and cache a cleaned polygon layer in BNG."""

    if cache_path.exists():
        if verbose:
            print(f"[pipeline] using cached {asset.name}: {cache_path}", flush=True)
        return gpd.read_parquet(cache_path)

    if verbose:
        print(f"[pipeline] building cached {asset.name} layer", flush=True)

    if asset.path.suffix == ".parquet":
        source = gpd.read_parquet(asset.path)
    else:
        previous_organize = os.environ.get("OGR_ORGANIZE_POLYGONS")
        os.environ["OGR_ORGANIZE_POLYGONS"] = "SKIP"
        try:
            source = pyogrio.read_dataframe(asset.path, layer=asset.layer, use_arrow=True)
        finally:
            if previous_organize is None:
                os.environ.pop("OGR_ORGANIZE_POLYGONS", None)
            else:
                os.environ["OGR_ORGANIZE_POLYGONS"] = previous_organize

    cleaned = repair_geometries(
        ensure_bng(source),
        allowed_geom_types=("Polygon", "MultiPolygon"),
    )
    cleaned.columns = cleaned.columns.str.lower()
    cleaned["source_dataset_name"] = asset.name
    cleaned["source_dataset_path"] = str(asset.path)
    cleaned["source_dataset_layer"] = asset.layer or ""
    cleaned["source_dataset_description"] = asset.description
    cleaned["source_dataset_original_crs"] = str(source.crs) if source.crs is not None else ""
    cleaned["source_geometry_handling"] = "ensure_bng|repair_geometries|polygon_filter"
    write_geoparquet(cleaned, cache_path)
    return cleaned


def _asset_cache_path(prefix: str, asset: DataAsset) -> Path:
    suffix = asset.path.stem.lower().replace(" ", "_")
    return Path("data/interim") / f"{prefix}_{suffix}_clean.parquet"


def _resolve_named_asset(
    *,
    kind: str,
    explicit_path: Path | None,
    explicit_layer: str | None,
    canonical_path: Path,
    candidates: tuple[Path, ...],
    description: str,
    require_dedicated: bool,
) -> DataAsset | None:
    path = _existing_path(explicit_path, candidates)
    if path is None and require_dedicated:
        raise FileNotFoundError(
            f"Canonical run requires dedicated {kind} data at {canonical_path}. "
            "Use the local-development pipeline or pass the dedicated path explicitly."
        )
    if path is None:
        return None
    return DataAsset(
        name=kind,
        path=path,
        layer=explicit_layer,
        description=description,
    )


def _source_record(
    *,
    label: str,
    source_name: str,
    asset: DataAsset | None,
    clean_path: Path | None,
) -> dict[str, str]:
    return {
        "label": label,
        "source_name": source_name,
        "path": str(asset.path) if asset is not None else "",
        "layer": (asset.layer or "") if asset is not None else "",
        "description": asset.description if asset is not None else "CORINE fallback proxy",
        "clean_path": str(clean_path) if clean_path is not None else "",
    }


def _run_metadata_path(out_dir: Path) -> Path:
    if out_dir == CANONICAL_RUN_METADATA_PATH.parent:
        return CANONICAL_RUN_METADATA_PATH
    return out_dir / RUN_METADATA_FILENAME


def _write_run_metadata(out_dir: Path, payload: dict[str, Any]) -> Path:
    return write_json(payload, _run_metadata_path(out_dir))


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
    flood_path: Path | None = None,
    flood_layer: str | None = None,
    peat_path: Path | None = None,
    peat_layer: str | None = None,
    cell_diameter_m: float = 1000,
    tile_size_m: float = 50_000,
    bird_max_records: int | None = None,
    mammal_max_records: int | None = None,
    verbose: bool = False,
    reuse_existing: bool = True,
    require_dedicated_flood_peat: bool = False,
    run_profile: str = "local_development",
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
    flood_asset = _resolve_named_asset(
        kind="flood",
        explicit_path=flood_path,
        explicit_layer=flood_layer,
        canonical_path=CANONICAL_FLOOD_PATH,
        candidates=DEFAULT_FLOOD_PATH_CANDIDATES,
        description="Dedicated flood opportunity layer used for the canonical published run.",
        require_dedicated=require_dedicated_flood_peat,
    )
    peat_asset = _resolve_named_asset(
        kind="peat",
        explicit_path=peat_path,
        explicit_layer=peat_layer,
        canonical_path=CANONICAL_PEAT_PATH,
        candidates=DEFAULT_PEAT_PATH_CANDIDATES,
        description="Dedicated peat opportunity layer used for the canonical published run.",
        require_dedicated=require_dedicated_flood_peat,
    )

    boundary_out = out_dir / "analysis_boundary.parquet"
    corine_out = out_dir / "corine_england_subset.parquet"
    habitat_out = out_dir / "habitat_proxy.parquet"
    bird_observation_out = out_dir / "bird_observations.parquet"
    mammal_observation_out = out_dir / "mammal_observations.parquet"
    grid_out = out_dir / "hex_grid.parquet"
    scores_out = out_dir / "hex_scores.parquet"
    run_metadata_out = _run_metadata_path(out_dir)
    grid_tiles_dir = out_dir / "grid_tiles"
    habitat_share_dir = out_dir / "feature_chunks" / "habitat_share"
    habitat_distance_dir = out_dir / "feature_chunks" / "distance"
    alc_feature_dir = out_dir / "feature_chunks" / "alc"
    flood_feature_dir = out_dir / "feature_chunks" / "flood"
    peat_feature_dir = out_dir / "feature_chunks" / "peat"
    bird_feature_dir = out_dir / "feature_chunks" / "bird_observations"
    mammal_feature_dir = out_dir / "feature_chunks" / "mammal_observations"

    if reuse_existing and scores_out.exists():
        if verbose:
            print(f"[pipeline] reusing existing scores: {scores_out}", flush=True)
        return {
            "boundary": boundary_out,
            "corine_subset": corine_out,
            "habitat_proxy": habitat_out,
            "bird_observations": bird_observation_out,
            "mammal_observations": mammal_observation_out,
            "grid": grid_out,
            "scores": scores_out,
            "run_metadata": run_metadata_out,
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

    flood_source_name = "corine_proxy"
    peat_source_name = "corine_proxy"
    flood_source = corine
    peat_source = corine
    flood_clean_path: Path | None = None
    peat_clean_path: Path | None = None

    if flood_asset is not None:
        if verbose:
            print("[pipeline] loading dedicated flood layer", flush=True)
        flood_clean_path = _asset_cache_path("flood", flood_asset)
        flood_source = _load_clean_vector_asset(
            flood_asset,
            cache_path=flood_clean_path,
            verbose=verbose,
        )
        flood_source_name = "dedicated_dataset"

    if peat_asset is not None:
        if verbose:
            print("[pipeline] loading dedicated peat layer", flush=True)
        peat_clean_path = _asset_cache_path("peat", peat_asset)
        peat_source = _load_clean_vector_asset(
            peat_asset,
            cache_path=peat_clean_path,
            verbose=verbose,
        )
        peat_source_name = "dedicated_dataset"

    if reuse_existing and habitat_out.exists():
        habitat = gpd.read_parquet(habitat_out)
    else:
        habitat = corine_habitat_proxy(corine, code_column="code_18")
        write_geoparquet(habitat, habitat_out)

    if reuse_existing and bird_observation_out.exists():
        bird_observations = gpd.read_parquet(bird_observation_out)
    else:
        if verbose:
            print("[pipeline] loading bird observations", flush=True)
        bird_observations = download_nbn_bird_observations(
            BIRD_OBSERVATION_CACHE_PATH,
            max_records=bird_max_records,
            verbose=verbose,
        )
        write_geoparquet(bird_observations, bird_observation_out)

    if reuse_existing and mammal_observation_out.exists():
        mammal_observations = gpd.read_parquet(mammal_observation_out)
    else:
        if verbose:
            print("[pipeline] loading mammal observations", flush=True)
        mammal_observations = download_nbn_mammal_observations(
            MAMMAL_OBSERVATION_CACHE_PATH,
            max_records=mammal_max_records,
            verbose=verbose,
        )
        write_geoparquet(mammal_observations, mammal_observation_out)

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
    if verbose:
        print("[pipeline] flood feature", flush=True)
    flood_feature = add_flood_opportunity_feature(
        grid,
        flood_source,
        code_column="code_18",
        source_name=flood_source_name,
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=flood_feature_dir,
    )
    if verbose:
        print("[pipeline] peat feature", flush=True)
    peat_feature = add_peat_opportunity_feature(
        grid,
        peat_source,
        code_column="code_18",
        source_name=peat_source_name,
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=peat_feature_dir,
    )
    if verbose:
        print("[pipeline] bird observation feature", flush=True)
    bird_feature = add_bird_observation_feature(
        grid,
        bird_observations,
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=bird_feature_dir,
    )
    if verbose:
        print("[pipeline] mammal observation feature", flush=True)
    mammal_feature = add_mammal_observation_feature(
        grid,
        mammal_observations,
        tile_size_m=tile_size_m,
        verbose=verbose,
        checkpoint_dir=mammal_feature_dir,
    )

    features = combine_feature_table(
        grid,
        habitat_share,
        habitat_distance,
        alc_feature,
        flood_feature,
        peat_feature,
        bird_feature,
        mammal_feature,
    )
    expected_full_hex_area_m2 = 3 * (3**0.5) / 2 * ((cell_diameter_m / 2) ** 2)
    features["cell_area_ratio"] = (
        features.geometry.area / expected_full_hex_area_m2
    ).clip(lower=0, upper=1)
    features = add_connectivity_score(features)
    features = add_restoration_opportunity_scores(features)
    features = add_boundary_penalty(features)
    features["priority_habitat_share"] = features["priority_habitat_share"].fillna(0) * 100
    features["run_profile"] = run_profile
    features["flood_feature_source"] = flood_source_name
    features["flood_source_path"] = str(flood_asset.path) if flood_asset is not None else ""
    features["flood_source_layer"] = flood_asset.layer or "" if flood_asset is not None else ""
    features["flood_clean_path"] = str(flood_clean_path) if flood_clean_path is not None else ""
    features["peat_feature_source"] = peat_source_name
    features["peat_source_path"] = str(peat_asset.path) if peat_asset is not None else ""
    features["peat_source_layer"] = peat_asset.layer or "" if peat_asset is not None else ""
    features["peat_clean_path"] = str(peat_clean_path) if peat_clean_path is not None else ""
    features = add_bird_observation_scores(features)
    features = add_mammal_observation_scores(features)
    features = add_biodiversity_observation_score(features)

    scored = apply_scenarios(features)

    write_geoparquet(
        gpd.GeoDataFrame(scored, geometry="geometry", crs=grid.crs),
        scores_out,
    )
    run_metadata = {
        "run_profile": run_profile,
        "out_dir": str(out_dir),
        "scores_path": str(scores_out),
        "boundary_path": str(boundary_path) if boundary_path is not None else "",
        "require_dedicated_flood_peat": require_dedicated_flood_peat,
        "canonical_contract": canonical_source_contract(),
        "active_sources": {
            "flood": _source_record(
                label="flood",
                source_name=flood_source_name,
                asset=flood_asset,
                clean_path=flood_clean_path,
            ),
            "peat": _source_record(
                label="peat",
                source_name=peat_source_name,
                asset=peat_asset,
                clean_path=peat_clean_path,
            ),
        },
    }
    _write_run_metadata(out_dir, run_metadata)

    outputs = {
        "boundary": boundary_out,
        "corine_subset": corine_out,
        "habitat_proxy": habitat_out,
        "bird_observations": bird_observation_out,
        "mammal_observations": mammal_observation_out,
        "grid": grid_out,
        "scores": scores_out,
        "run_metadata": run_metadata_out,
    }
    return outputs
