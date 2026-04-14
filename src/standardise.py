from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from src.ingest import ensure_bng, repair_geometries, write_geoparquet


def standardise_layer(
    source_path: Path,
    out_path: Path,
    *,
    layer: str | None = None,
    clip_to: gpd.GeoDataFrame | None = None,
    lowercase_columns: bool = True,
) -> gpd.GeoDataFrame:
    """Read, reproject, optionally clip, and save a geospatial layer."""

    gdf = gpd.read_file(source_path, layer=layer)
    gdf = ensure_bng(gdf)
    gdf = repair_geometries(gdf)

    if lowercase_columns:
        gdf.columns = gdf.columns.str.lower()

    if clip_to is not None:
        gdf = gpd.clip(gdf, clip_to)

    write_geoparquet(gdf, out_path)
    return gdf
