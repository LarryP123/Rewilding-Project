from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def repair_geometries(
    gdf: gpd.GeoDataFrame,
    allowed_geom_types: tuple[str, ...] | None = None,
) -> gpd.GeoDataFrame:
    """Repair invalid geometries and drop empty outputs."""

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
