from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import warnings

import geopandas as gpd
import pandas as pd
import shapely
from shapely.errors import GEOSException
from shapely.geometry import box

BNG_EPSG = 27700
CORINE_EPSG = 3035


@dataclass(frozen=True)
class DataAsset:
    """Minimal metadata for a source dataset tracked in the project."""

    name: str
    path: Path
    layer: str | None = None
    description: str = ""


def load_vector(asset: DataAsset, bbox: tuple[float, float, float, float] | None = None) -> gpd.GeoDataFrame:
    """Load a vector dataset from disk."""

    return gpd.read_file(asset.path, layer=asset.layer, bbox=bbox)


def ensure_bng(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return geometry in British National Grid."""

    if gdf.crs is None:
        raise ValueError("Input GeoDataFrame has no CRS.")
    return gdf.to_crs(epsg=BNG_EPSG)


def write_geoparquet(gdf: gpd.GeoDataFrame, out_path: Path) -> Path:
    """Persist a GeoDataFrame as GeoParquet, creating parent directories as needed."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(out_path)
    return out_path


def write_json(payload: dict[str, object], out_path: Path) -> Path:
    """Persist a JSON sidecar with stable formatting."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def repair_geometries(
    gdf: gpd.GeoDataFrame,
    allowed_geom_types: tuple[str, ...] | None = None,
) -> gpd.GeoDataFrame:
    """Repair invalid geometries and drop empty outputs."""

    non_empty = gdf.loc[
        gdf.geometry.apply(lambda geom: geom is not None and not geom.is_empty)
    ].copy()
    non_empty = gpd.GeoDataFrame(non_empty, geometry=gdf.geometry.name, crs=gdf.crs)

    if not non_empty.empty and non_empty.geometry.is_valid.all():
        if allowed_geom_types is None:
            return non_empty
        valid_types = non_empty.geometry.geom_type.isin(allowed_geom_types)
        if valid_types.all():
            return non_empty
        return non_empty.loc[valid_types].copy()

    repaired = gdf.copy()

    def _repair(geometry):
        if geometry is None or geometry.is_empty:
            return None
        try:
            if geometry.is_valid:
                return geometry
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                return shapely.make_valid(geometry)
        except (AttributeError, GEOSException):
            try:
                return geometry.buffer(0)
            except GEOSException:
                return None

    repaired_geometry = gdf.geometry.apply(_repair)
    attrs = pd.DataFrame(gdf.drop(columns=[gdf.geometry.name], errors="ignore")).copy()
    attrs["geometry"] = repaired_geometry.values
    repaired = gpd.GeoDataFrame(attrs, geometry="geometry", crs=gdf.crs)
    repaired = repaired.loc[
        repaired.geometry.apply(lambda geom: geom is not None and not geom.is_empty)
    ].copy()
    repaired = gpd.GeoDataFrame(repaired, geometry="geometry", crs=gdf.crs)
    if allowed_geom_types is not None:
        repaired = repaired.loc[repaired.geometry.geom_type.isin(allowed_geom_types)].copy()
        repaired = gpd.GeoDataFrame(repaired, geometry="geometry", crs=gdf.crs)
    return repaired


def england_bbox_wgs84() -> gpd.GeoDataFrame:
    """Return a broad England-focused bounding box in WGS84."""

    return gpd.GeoDataFrame(geometry=[box(-6.5, 49.8, 2.2, 56.2)], crs="EPSG:4326")


def england_bbox_bng() -> gpd.GeoDataFrame:
    """Return the broad England-focused bounding box in British National Grid."""

    return gpd.GeoDataFrame(geometry=[box(0, 0, 700000, 700000)], crs=f"EPSG:{BNG_EPSG}")


def england_bbox_corine() -> tuple[float, float, float, float]:
    """Return a CORINE-compatible bbox for an England-focused subset."""

    bounds = england_bbox_wgs84().to_crs(epsg=CORINE_EPSG).total_bounds
    return tuple(bounds)


def _curl_json(base_url: str, params: list[tuple[str, object]]) -> dict:
    """Fetch a JSON payload with curl so networked downloads work in this environment."""

    command = ["curl", "-sS", "-L", "-G", base_url]
    for key, value in params:
        command.extend(["--data-urlencode", f"{key}={value}"])

    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def download_nbn_observations(
    cache_path: Path,
    *,
    taxon_label: str,
    taxon_filters: list[str],
    data_resource_uid: str = "dr3717",
    state_province: str = "England",
    year_from: int = 2015,
    max_coordinate_uncertainty_m: float = 2000,
    page_size: int = 1000,
    max_records: int | None = None,
    verbose: bool = False,
) -> gpd.GeoDataFrame:
    """Download and cache observation-based records from NBN Atlas."""

    if cache_path.exists():
        return gpd.read_parquet(cache_path)

    if page_size <= 0:
        raise ValueError("page_size must be positive.")
    if max_records is not None and max_records <= 0:
        raise ValueError("max_records must be positive when provided.")

    base_url = "https://records-ws.nbnatlas.org/occurrences/search"
    fq_params = [
        *taxon_filters,
        f"data_resource_uid:{data_resource_uid}",
        f"stateProvince:{state_province}",
        f"year:[{year_from} TO *]",
        f"coordinate_uncertainty:[0 TO {int(max_coordinate_uncertainty_m)}]",
    ]

    initial_page_size = min(page_size, max_records) if max_records is not None else page_size

    first_payload = _curl_json(
        base_url,
        [("q", "*:*"), *[("fq", value) for value in fq_params], ("pageSize", initial_page_size), ("startIndex", 0)],
    )

    total_records = int(first_payload.get("totalRecords", 0))
    if max_records is not None:
        total_records = min(total_records, max_records)

    rows: list[dict[str, object]] = []

    def _append_rows(payload: dict) -> None:
        for occurrence in payload.get("occurrences", []):
            latitude = occurrence.get("decimalLatitude")
            longitude = occurrence.get("decimalLongitude")
            species_guid = occurrence.get("speciesGuid")
            if latitude is None or longitude is None or species_guid in (None, ""):
                continue
            rows.append(
                {
                    "species_guid": species_guid,
                    "species_name": occurrence.get("species"),
                    "taxon_label": taxon_label,
                    "year": occurrence.get("year"),
                    "coordinate_uncertainty_m": occurrence.get("coordinateUncertaintyInMeters"),
                    "data_resource_uid": occurrence.get("dataResourceUid"),
                    "data_resource_name": occurrence.get("dataResourceName"),
                    "basis_of_record": occurrence.get("basisOfRecord"),
                    "license": occurrence.get("license"),
                    "geometry": shapely.Point(float(longitude), float(latitude)),
                }
            )

    _append_rows(first_payload)
    if verbose:
        print(f"[{taxon_label}] fetched {min(len(rows), total_records)} / {total_records}", flush=True)

    start_index = initial_page_size
    while start_index < total_records:
        fetch_size = min(page_size, total_records - start_index)
        payload = _curl_json(
            base_url,
            [
                ("q", "*:*"),
                *[("fq", value) for value in fq_params],
                ("pageSize", fetch_size),
                ("startIndex", start_index),
            ],
        )
        _append_rows(payload)
        start_index += fetch_size
        if verbose:
            print(f"[{taxon_label}] fetched {min(len(rows), total_records)} / {total_records}", flush=True)

    frame = pd.DataFrame(rows)
    if frame.empty:
        result = gpd.GeoDataFrame(frame, geometry=[], crs="EPSG:4326")
    else:
        result = gpd.GeoDataFrame(frame, geometry="geometry", crs="EPSG:4326")
        result = ensure_bng(result)

    write_geoparquet(result, cache_path)
    return result


def download_nbn_bird_observations(
    cache_path: Path,
    *,
    data_resource_uid: str = "dr3717",
    state_province: str = "England",
    year_from: int = 2015,
    max_coordinate_uncertainty_m: float = 2000,
    page_size: int = 1000,
    max_records: int | None = None,
    verbose: bool = False,
) -> gpd.GeoDataFrame:
    """Download and cache observation-based bird records from NBN Atlas."""

    return download_nbn_observations(
        cache_path,
        taxon_label="bird_observations",
        taxon_filters=["class:Aves"],
        data_resource_uid=data_resource_uid,
        state_province=state_province,
        year_from=year_from,
        max_coordinate_uncertainty_m=max_coordinate_uncertainty_m,
        page_size=page_size,
        max_records=max_records,
        verbose=verbose,
    )


def download_nbn_mammal_observations(
    cache_path: Path,
    *,
    data_resource_uid: str = "dr3717",
    state_province: str = "England",
    year_from: int = 2015,
    max_coordinate_uncertainty_m: float = 2000,
    page_size: int = 1000,
    max_records: int | None = None,
    verbose: bool = False,
) -> gpd.GeoDataFrame:
    """Download and cache observation-based mammal records from NBN Atlas."""

    return download_nbn_observations(
        cache_path,
        taxon_label="mammal_observations",
        taxon_filters=["class:Mammalia"],
        data_resource_uid=data_resource_uid,
        state_province=state_province,
        year_from=year_from,
        max_coordinate_uncertainty_m=max_coordinate_uncertainty_m,
        page_size=page_size,
        max_records=max_records,
        verbose=verbose,
    )
